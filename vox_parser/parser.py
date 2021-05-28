from .parser_exceptions import *
from .models import *
from .default_palette import default_palette
from nbt.nbt import *
from io import BytesIO
import typing
import struct
from enum import Enum
import logging

log = logging.getLogger(__name__)


MATERIALS = [(0, 'plastic'),
            (1, 'roughness'),
            (2, 'specular'),
            (3, 'IOR'),
            (4, 'attenuation'),
            (5, 'power'),
            (6, 'glow'),
            (7, 'isTotalPower') ]


def list_to_byte_array(block_data):
    return BytesIO(len(block_data).to_bytes(4, byteorder='big') + bytearray(block_data))


def compare_bits(value, offset):
    mask = 1 << offset
    return value & mask


class Constants(Enum):
    HEADER_TYPE = 'VOX'
    VERSION = 150
    MAIN_CHUNK = 'MAIN'
    PACK_CHUNK = 'PACK'
    SIZE_CHUNK = 'SIZE'
    XYZI_CHUNK = 'XYZI'
    RGBA_CHUNK = 'RGBA'
    MATERIAL_CHUNK = 'MATT'


class Voxels:
    models: typing.List[Model]
    palette = [Color(*tuple(i.to_bytes(4, 'little'))) for i in default_palette ]
    materials = []
    default_palette = False
    colors = Colors()
    _schematics: Schematics = None

    def __init__(self, models, palette=None, materials=None):
        self.models = models
        self.default_palette = not palette
        if materials:
            self.materials = materials
        if palette:
            self.palette = palette
        for color in self.palette:
            self.colors.add(color)
        print("using default palette")

    @property
    def schematics(self):
        return self._schematics

    def parse_schematics(self, model, default_block=1, blocks_palette=None):
        if not self._schematics:
            self._schematics = Schematics(model, self.colors, self.palette, default_block, blocks_palette)
        else:
            self.schematics.parse(model, self.colors, self.palette, default_block, blocks_palette)

    def save_schematic(self, output, default_block=1, blocks_palette=None):
        self.parse_schematics(self.models[0], default_block, blocks_palette)
        model = self.models[0]
        width, length, height = model.size
        blocks = self.schematics.blocks_type
        blocks_ext = self.schematics.blocks_meta
        nbt_file = NBTFile()
        nbt_file.name = "Schematic"
        nbt_file.tags.append(TAG_Short(name="Width", value=width))
        nbt_file.tags.append(TAG_Short(name="Length", value=length))
        nbt_file.tags.append(TAG_Short(name="Height", value=height))
        nbt_file.tags.append(TAG_String(name="Materials", value="Alpha"))
        nbt_file.tags.append(TAG_Byte_Array(name="Blocks", buffer=list_to_byte_array(blocks)))
        nbt_file.tags.append(TAG_Byte_Array(name="Data", buffer=list_to_byte_array(blocks_ext)))
        nbt_file.tags.append(TAG_List(name="Entities", type=TAG_Compound))
        nbt_file.tags.append(TAG_List(name="TileEntities", type=TAG_Compound))
        nbt_file.write_file(output)


class Chunk:
    chunk_id: str
    size = Size(0, 0, 0)
    content = b''
    voxels = []
    chunks = []
    models = []
    palette = []
    material = Material(0, 0, 0, {})

    def __init__(self, chunk_id, content = None, chunks = None):
        self.chunk_id = chunk_id.decode("utf8").strip()
        if content:
            self.content = content
        if chunks:
            self.chunks = chunks
        self._parse_chunk()
    
    def _parse_chunk(self):
        if self.chunk_id == Constants.MAIN_CHUNK.value:
            if len(self.content):
                raise ContentNotEmpty("Expected empty content for main chunk.")
        elif self.chunk_id == Constants.PACK_CHUNK.value:
            models = struct.unpack_from('i', self.content)[0]
            if len(models) < 0:
                raise ParserException('Expected chunk to have at least 1 model.')
        elif self.chunk_id == Constants.SIZE_CHUNK.value:
            self.size = Size(*struct.unpack_from('iii', self.content))
        elif self.chunk_id == Constants.XYZI_CHUNK.value:
            # Block with voxels
            blocks_amount = struct.unpack_from('i', self.content)
            if len(blocks_amount) < 1:
                raise ParserException('Expected at least 1 element.')
            blocks_amount = blocks_amount[0]
            print(f'xyzi block with {blocks_amount} voxels (len {len(self.content)})')
            self.voxels = []
            for i in range(blocks_amount):
                result = struct.unpack_from('BBBB', self.content, 4+4*i)
                self.voxels.append(Voxel(*result))
        elif self.chunk_id == Constants.RGBA_CHUNK.value:
            palette = []
            for i in range(255):
                color = Color(*struct.unpack_from('BBBB', self.content, 4*i))
                palette.append(color)
            self.palette = palette
        elif self.chunk_id == Constants.MATERIAL_CHUNK.value:
            material_id, material_type, weight, flags = struct.unpack_from('iifi', self.content)
            properties = {}
            offset = 16
            for bit, field in MATERIALS:
                # value for isTotalPower doesn't exists? should i check it once more
                if compare_bits(flags, bit) and bit < 7 :
                    properties[field] = struct.unpack_from('f', self.content, offset)
                    offset += 4
            self.material = Material(material_id, material_type, weight, properties)
        else:
            raise UnknownChunkType("Chunk type is unknown at id {self.id}")


class VoxelParser:
    offset = 0
    content: bytes
    _default_palette = False  # should we try to use default palette with default blocks id or not

    def __init__(self, use_default_palette=False):
        self._default_palette = use_default_palette

    def unpack(self, __format):
        if not self.content:
            raise ContentIsNotLoaded("Content of vox file wasn't properly loaded    ")
        result = struct.unpack_from(__format, self.content, self.offset)
        self.offset += struct.calcsize(__format)
        return result

    def get_header_and_version(self):
        header, version = self.unpack('4si')
        if header.decode("utf8").strip() != Constants.HEADER_TYPE.value:
            raise HeaderException("It's not vox file!")
        if version != Constants.VERSION.value:
            raise UnknownVersionException("Unknown vox version!")

    def _parse_chunk(self):
        chunk_id, chunk_length, chunk_children = self.unpack("4sii")
        # log.debug("Found chunk id %s / len %s / children %s", chunk_id, N, M)
        print("Found chunk id %s / len %s / children %s" % (chunk_id, chunk_length, chunk_children))
        content = self.unpack('%ds'%chunk_length)
        if len(content) < 1:
            raise NotEnoughChunkContent("Not enough chunk content! Check file!")
        
        content = content[0]

        start_position = self.offset
        chunks = []
        while self.offset < start_position + chunk_children:
            chunks.append(self._parse_chunk())
        return Chunk(chunk_id, content, chunks)

    def _parse_model(self, size: Chunk, xyzi: Chunk):
        if size.chunk_id != Constants.SIZE_CHUNK.value:
            raise UnknownChunkType(f'Expected Size chunk, got {size.chunk_id}')
        if xyzi.chunk_id != Constants.XYZI_CHUNK.value:
            raise UnknownChunkType(f'Expected XYZI chunk, got {size.chunk_id}')
        return Model(size.size, xyzi.voxels)

    def _parse_chunks(self):
        self.get_header_and_version()
        main = self._parse_chunk()

        if main.chunk_id != Constants.MAIN_CHUNK.value:
            raise ParserException("Main chunk not found")

        chunks = list(reversed(main.chunks))
        if chunks[-1].chunk_id == Constants.PACK_CHUNK.value:
            models_number = chunks.pop().models
        else:
            models_number = 1
        
        print("file has %d models" % models_number)

        models = []
    
        for _ in range(models_number):
            result = self._parse_model(chunks.pop(), chunks.pop())
            models.append(result)
        
        if chunks and chunks[0].chunk_id == Constants.RGBA_CHUNK.value:
            palette = chunks.pop().palette
        else:
            palette = None

        materials = [chunk.material for chunk in chunks]
        return Voxels(models, palette, materials)
    
    def read_from_file(self, file_path) -> Voxels:
        self.offset = 0
        self.content = b''
        self._default_palette = False
        with open(file_path, 'rb') as file:
            self.content = file.read()
        return self._parse_chunks()    


if __name__ == "__main__":
    voxels = VoxelParser().read_from_file("./test.vox")
