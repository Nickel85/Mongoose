#include <process.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <windows.h>

#include "mongoose_py.inc"

static void quote_arg(const char *input, char *output, size_t output_size) {
    size_t j = 0;
    output[j++] = '"';
    for (size_t i = 0; input[i] != '\0' && j + 2 < output_size; i++) {
        if (input[i] == '"') {
            output[j++] = '\\';
        }
        output[j++] = input[i];
    }
    output[j++] = '"';
    output[j] = '\0';
}

static int ensure_parent_directory(const char *path) {
    char buffer[MAX_PATH * 2];
    snprintf(buffer, sizeof(buffer), "%s", path);

    for (char *cursor = buffer; *cursor != '\0'; cursor++) {
        if (*cursor == '\\' || *cursor == '/') {
            char original = *cursor;
            *cursor = '\0';
            if (strlen(buffer) > 2) {
                CreateDirectoryA(buffer, NULL);
            }
            *cursor = original;
        }
    }

    return 0;
}

static int write_embedded_cli(const char *script_path) {
    ensure_parent_directory(script_path);

    FILE *file = fopen(script_path, "wb");
    if (!file) {
        fprintf(stderr, "Could not write mongoose CLI to %s\n", script_path);
        return 1;
    }

    size_t written = fwrite(MONGOOSE_PY, 1, MONGOOSE_PY_LEN, file);
    fclose(file);

    if (written != MONGOOSE_PY_LEN) {
        fprintf(stderr, "Could not write complete mongoose CLI to %s\n", script_path);
        return 1;
    }

    return 0;
}

int main(int argc, char **argv) {
    char local_app_data[MAX_PATH];
    DWORD length = GetEnvironmentVariableA("LOCALAPPDATA", local_app_data, MAX_PATH);
    if (length == 0 || length >= MAX_PATH) {
        fprintf(stderr, "LOCALAPPDATA is not set.\n");
        return 1;
    }

    char script[MAX_PATH * 2];
    snprintf(script, sizeof(script), "%s\\Agents\\mongoose\\mongoose.py", local_app_data);

    if (write_embedded_cli(script) != 0) {
        return 1;
    }

    char quoted_script[MAX_PATH * 2 + 4];
    quote_arg(script, quoted_script, sizeof(quoted_script));

    size_t command_size = 8192;
    char *command = (char *)calloc(command_size, sizeof(char));
    if (!command) {
        fprintf(stderr, "Could not allocate command buffer.\n");
        return 1;
    }

    snprintf(command, command_size, "python %s", quoted_script);
    for (int i = 1; i < argc; i++) {
        char quoted_arg[2048];
        quote_arg(argv[i], quoted_arg, sizeof(quoted_arg));
        strncat(command, " ", command_size - strlen(command) - 1);
        strncat(command, quoted_arg, command_size - strlen(command) - 1);
    }

    int result = system(command);
    free(command);
    return result;
}
