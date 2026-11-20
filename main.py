from c_package.c_maze import get_maze
import sys

if __name__ == "__main__":
    W, H = int(sys.argv[1]), int(sys.argv[2]) # Width and height must be odd
    difficulty = int(sys.argv[3]) # Integer from 0-10; 0 has smallest possible # of walls, 10 guarantees exactly one solution
    maze = get_maze(W, H, difficulty)

    symbols = {0: "  ", 1: "##", 2: "S ", 3: "E "}
    for row in maze:
        print("".join(symbols[cell] for cell in row))

    #print(maze[3]) #Access a row
    #print(maze[3][5]) #Access a particular cell