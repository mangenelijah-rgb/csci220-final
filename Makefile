# Compiler and flags
CC       := gcc
CFLAGS   := -Wall -Wextra -O3 -fPIC
CPPFLAGS := -Iinclude -MMD -MP
LDFLAGS  := -shared

# Directories
SRC_DIR   := src
INC_DIR   := include
BUILD_DIR := build
OBJ_DIR   := $(BUILD_DIR)/obj

# Automatically detect OS for shared library extension (.dll on Windows, .so on Linux/macOS)
ifeq ($(OS),Windows_NT)
    TARGET := $(BUILD_DIR)/maze.dll
else
    TARGET := $(BUILD_DIR)/maze.so
endif

# Find all .c files in src/ and any nested subdirectories
SRCS := $(shell find $(SRC_DIR) -name '*.c')

# Map each src/path/file.c to build/obj/path/file.o
OBJS := $(patsubst $(SRC_DIR)/%.c, $(OBJ_DIR)/%.o, $(SRCS))

# Map each .o file to a corresponding .d dependency file
DEPS := $(OBJS:.o=.d)

# Default target
all: $(TARGET)

# Link all object files into the shared library
$(TARGET): $(OBJS)
	@mkdir -p $(dir $@)
	$(CC) $(LDFLAGS) -o $@ $^

# Compile .c files into .o files and create nested build directories on the fly
$(OBJ_DIR)/%.o: $(SRC_DIR)/%.c
	@mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

# Include auto-generated header dependency rules
-include $(DEPS)

# Clean build artifacts
clean:
	rm -rf $(BUILD_DIR)

.PHONY: all clean
