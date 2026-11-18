#ifndef MAZE_H
#define MAZE_H

#include <stdint.h>

// Handle Windows DLL symbol exporting vs. Linux/macOS default visibility
#ifdef _WIN32
    #define EXPORT __declspec(dllexport)
#else
    #define EXPORT __attribute__((visibility("default")))
#endif

// Standard cell values
typedef enum {
    CELL_PATH  = 0,
    CELL_WALL  = 1,
    CELL_START = 2,
    CELL_END   = 3
} MazeCell;

EXPORT uint8_t* generate_maze(int width, int height);
EXPORT void free_maze(uint8_t *grid);

void carve(uint8_t *grid, int width, int height, int x, int y);
void shuffle(int *array, int n);

#endif
