#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <math.h>
#include "maze.h"

// Bitwise helper functions
static inline int get_bit(const uint32_t *grid, int idx) {
    return (grid[idx >> 5] >> (idx & 31)) & 1U;
}

static inline void set_path(uint32_t *grid, int idx) {
    grid[idx >> 5] &= ~(1U << (idx & 31)); // Set bit to 0
}

// Compact state struct (8 bytes per frame instead of ~64+ bytes on the call stack)
typedef struct {
    int16_t x;
    int16_t y;
    uint8_t dirs[4];
    uint8_t idx;
} CarveFrame;

static void shuffle(uint8_t *array, int n) {
    for (int i = 0; i < n - 1; i++) {
        int j = i + rand() / (RAND_MAX / (n - i) + 1);
        uint8_t temp = array[j];
        array[j] = array[i];
        array[i] = temp;
    }
}

void carve(uint32_t *grid, int width, int height, int start_x, int start_y, int percentWall) {
    // Only odd coordinates are visited, so max depth is at most (width / 2) * (height / 2)
    size_t max_depth = (size_t)((width / 2 + 1) * (height / 2 + 1));
    CarveFrame *stack = (CarveFrame *)malloc(max_depth * sizeof(CarveFrame));
    if (!stack) return;

    const int dx[] = {0, 2, 0, -2};
    const int dy[] = {-2, 0, 2, 0};

    // Push the initial starting cell onto the stack
    int top = 0;
    stack[0] = (CarveFrame){
        .x = (int16_t)start_x,
        .y = (int16_t)start_y,
        .dirs = {0, 1, 2, 3},
        .idx = 0
    };
    shuffle(stack[0].dirs, 4);

    while (top >= 0) {
        CarveFrame *curr = &stack[top];

        // If all 4 directions for this cell are checked, pop and backtrack
        if (curr->idx >= 4) {
            top--;
            continue;
        }

        int dir = curr->dirs[curr->idx++];
        int nx = curr->x + dx[dir];
        int ny = curr->y + dy[dir];

        if (nx > 0 && nx < width - 1 && ny > 0 && ny < height - 1) {
            int next_idx = ny * width + nx;
            int mid_idx = (curr->y + dy[dir] / 2) * width + (curr->x + dx[dir] / 2);

            if (get_bit(grid, next_idx) == 1) { // Unvisited wall
                set_path(grid, mid_idx);
                set_path(grid, next_idx);

                // Push the new cell onto the stack to explore it next
                top++;
                stack[top] = (CarveFrame){
                    .x = (int16_t)nx,
                    .y = (int16_t)ny,
                    .dirs = {0, 1, 2, 3},
                    .idx = 0
                };
                shuffle(stack[top].dirs, 4);
            } else if ((rand() % 100) >= percentWall) {
                set_path(grid, mid_idx);
            }
        }
    }

    free(stack);
}


uint32_t* generate_maze(int width, int height, int difficulty) {
    srand((unsigned int)time(NULL));

    int total_cells = width * height;
    // Ceiling division: (total_cells + 31) / 32
    size_t num_ints = (total_cells + 31) >> 5;

    uint32_t *grid = (uint32_t*)malloc(num_ints * sizeof(uint32_t));
    if (!grid) return NULL;

    // Fill all bits with 1 (0xFF sets every byte to 11111111)
    memset(grid, 0xFF, num_ints * sizeof(uint32_t));

    int percentWall = (int)(100 * (log((7.4 * difficulty) + 1) / log(75)));

    // Carve starting at (1, 1)
    set_path(grid, width + 1);
    carve(grid, width, height, 1, 1, percentWall);

    return grid;
}

void free_maze(uint32_t *grid) {
    free(grid);
}
