#include <stdint.h>
#include <stdlib.h>
#include <time.h>
#include <maze.h>

// Fisher-Yates shuffle algorithm; randomly change directions
void shuffle(int *array, int n) {
    for (int i = 0; i < n - 1; i++) {
        int j = i + rand() / (RAND_MAX / (n - i) + 1);
        int temp = array[j];
        array[j] = array[i];
        array[i] = temp;
    }
}

void carve(uint8_t *grid, int width, int height, int x, int y) {
    int directions[] = {0, 1, 2, 3};
    shuffle(directions, 4);

    int dx[] = {0, 2, 0, -2};
    int dy[] = {-2, 0, 2, 0};

    for (int i = 0; i < 4; i++) {
        int dir = directions[i];
        int nx = x + dx[dir];
        int ny = y + dy[dir];

        if (nx > 0 && nx < width - 1 && ny > 0 && ny < height - 1) {
            // Convert 2D coordinates (ny, nx) to 1D index: y * width + x
            if (grid[ny * width + nx] == 1) { //if (nx,ny) is a wall
                grid[(y + dy[dir] / 2) * width + (x + dx[dir] / 2)] = 0;
                grid[ny * width + nx] = 0; // Set (nx,ny) and (nx-1,ny-1) to paths
                carve(grid, width, height, nx, ny); //Recursive call until algorithm encounters a path or array boundary
            } // After recursive call returns, for loop checks the next direction
        }
    }
}

// Function to generate and return the maze
// Returns a pointer to an array [Row1,Row2,...,RowH] where Row = [Cell1,Cell2,...,CellW]
// and  Cell = (1 = Wall, 0 = Path, 2 = Start, 3 = End)
uint8_t* generate_maze(int width, int height) {
    srand((unsigned int)time(NULL));

    // Allocate 1D array
    uint8_t *grid = (uint8_t*)malloc(width * height * sizeof(uint8_t));
    if (!grid) return NULL;

    // Fill with walls (1)
    for (int i = 0; i < width * height; i++) {
        grid[i] = 1;
    }

    // Carve starting at (1, 1)
    grid[width + 1] = 0;
    carve(grid, width, height, 1, 1);

    // Set Start = 2 and End = 3
    grid[width] = 2;
    grid[(height - 2) * width + (width - 1)] = 3;

    return grid;
}

// Exported function to prevent memory leaks
void free_maze(uint8_t *grid) {
    free(grid);
}
