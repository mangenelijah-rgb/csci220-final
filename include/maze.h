#ifndef MAZE_H
#define MAZE_H

#include <stdint.h>

#ifdef _WIN32
    #define EXPORT __declspec(dllexport)
#else
    #define EXPORT __attribute__((visibility("default")))
#endif

EXPORT uint32_t* generate_maze(int width, int height, int difficulty);
EXPORT void free_maze(uint32_t *grid);

void carve(uint32_t *grid, int width, int height, int x, int y, int percentWall);

#endif
