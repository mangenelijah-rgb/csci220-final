from c_package.c_maze import get_maze

if __name__ == "__main__":
    W, H = 23, 71
    maze = get_maze(W, H)

    symbols = {0: "  ", 1: "##", 2: "S ", 3: "E "}
    for row in maze:
        print("".join(symbols[cell] for cell in row))

    #print(maze[3]) #Access a row
    #print(maze[3][5]) #Access a particular cell
