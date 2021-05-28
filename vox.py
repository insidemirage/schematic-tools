from vox_parser import VoxelParser, Color

BLOCK_SIZE = 5
INPUT_FOLDER = './voxels/{}'

colors_to_blocks = [{'color': Color(255, 0, 0, 255), 'numeric_id': '35:14'},
                    {'color': Color(0,19, 171, 255), 'numeric_id': '35:11'},
                    {'color': Color(228, 209, 11, 255), 'numeric_id': '35:4'},
                    {'color': Color(34, 75, 17, 255), 'numeric_id': '35:13'}]


def main():
    vox = VoxelParser()
    data = vox.read_from_file(INPUT_FOLDER.format('./test.vox'))
    data.save_schematic('./test.schem')
    data = vox.read_from_file(INPUT_FOLDER.format('./test2.vox'))
    data.save_schematic('./test2.schem')
    data = vox.read_from_file(INPUT_FOLDER.format('./test3.vox'))
    data.save_schematic('./test3.schem', 1, colors_to_blocks)


if __name__ == '__main__':
    main()
