#include <img/img.h>
#include <io/io.h>
#include <stdio.h>
#include <string.h>

int main(int argc, char **argv)
{
    int rc;
    img_t img = {0};
    img_lib_t ilib = NULL;
    const char *filename;

    if (argc != 2)
    {
        fprintf(stderr, "Usage: %s <image file>\n", argv[0]);
        return -1;
    }

    filename = argv[1];

    if ((rc = img_lib_attach(&ilib)) != IMG_ERR_OK)
    {
        fprintf(stderr, "img_lib_attach() failed: %d\n", rc);
        return -1;
    }

    if ((rc = img_load_file(ilib, filename, NULL, &img)) != IMG_ERR_OK)
    {
        fprintf(stderr, "img_load_file() (load) failed: %d\n", rc);
        perror("img_load_file");
        return -1;
    }

    img_lib_detach(ilib);
}
