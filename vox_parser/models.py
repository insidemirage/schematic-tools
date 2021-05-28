import os
import json
from dataclasses import dataclass
from math import sqrt


@dataclass
class Material:
    id: int
    type: int
    weight: int
    properties: dict


@dataclass
class Size:
    x: int
    y: int
    z: int

    def __iter__(self):
        return iter([self.x, self.y, self.z])


@dataclass
class Model:
    size: Size
    voxels: list


@dataclass
class Color:
    r: int
    g: int
    b: int
    a: int

    def __str__(self) -> str:
        return f"Red: {self.r} Green: {self.g} Blue: {self.b} Alpha: {self.a}"

    def __iter__(self):
        return iter([self.r, self.g, self.b, self.a])

    def __eq__(self, other):
        return other.r == self.r and other.g == self.g and other.b == self.b and other.a and self.a

    def get_nearest(self, blocks, block_type="solid"):
        color_diffs = []

        for block in blocks:
            if block["type"] != block_type:
                continue
            cr, cg, cb, _ = block["color"]
            color_diff = sqrt(abs(cr - self.r) ** 2 + abs(cg - self.g) ** 2 + abs(cb - self.b) ** 2)
            color_diffs.append({"diff": color_diff, "block": block})

        if len(color_diffs) == 0:
            return blocks[0]
        res = min(color_diffs, key=lambda x: x["diff"])["block"]
        return res


@dataclass
class Voxel:
    x: int
    y: int
    z: int
    color: int


# i know there's my ways to do that more easier
# but i pick this one because i'd like to have abstraction
class Colors:
    colors = []

    def __init__(self, colors=None):
        if colors:
            self.colors = colors

    def __str__(self) -> str:
        return ",".join([f'({item})' for item in self.colors])

    def __iter__(self):
        return iter(self.colors)

    def json(self):
        result = []
        for color in self.colors:
            result.append({
                "r": color.r,
                "g": color.g,
                "b": color.b,
                "a": color.a
            })
        return json.dumps(result)

    def add(self, color: Color):
        colors = list(filter(lambda x: x == color, self.colors))
        if len(colors) == 0:
            self.colors.append(color)


class Schematics:
    blocks_type = []
    blocks_meta = []

    def __init__(self, model, colors, palette, default_block=1, blocks_palette=None):
        self.parse(model, colors, palette, default_block, blocks_palette)

    def parse(self, model, colors, palette, default_block=1, blocks_palette=None):
        width, length, height = model.size
        blocks = [0] * (width * length * height)
        blocks_ext = blocks.copy()
        default_block = {"numeric_id": str(default_block)}
        blocks_id = {}

        if not blocks_palette:
            with open(os.path.join(os.path.dirname(__file__), "./blocks.json")) as file:
                data = json.load(file)
            blocks_palette = [{"color": Color(*i["color"], 255), "numeric_id": i["numeric_id"], "type": i["type"]}
                              for i in data]
            for color in colors:
                blocks_id[str(color)] = color.get_nearest(blocks_palette)["numeric_id"]
        else:
            for item in blocks_palette:
                blocks_id[str(item["color"])] = item["numeric_id"]

        for voxel in model.voxels:
            z, x, y, color = voxel.x, voxel.y, voxel.z, voxel.color
            # -1 because colors starts from 1 and palette from 0
            block = blocks_id.get(str(palette[color - 1]), default_block).split(":")
            meta = 0
            if len(block) == 2:
                meta = int(block[-1])
            blocks[(y * length + z) * width + x] = int(block[0])
            blocks_ext[(y * length + z) * width + x] = meta

        self.blocks_type = blocks
        self.blocks_meta = blocks_ext
