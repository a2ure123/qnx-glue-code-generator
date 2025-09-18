#include <stddef.h>
#include <dirent.h>
#include <stdint.h>
#include <string.h>

#define D_GETFLAG 1
#define D_SETFLAG 2
#define QNX_ENOSYS 89

struct qnx_dirent {
	uint64_t d_ino;
	uint64_t d_offset;
	int16_t d_reclen;
	int16_t d_namelen;
	char d_name[1];
};

int dircntl(DIR *dir, int cmd, ...)
{
	return 0;
}

struct qnx_dirent *_qnx_readdir(DIR *dir)
{
	struct dirent local;
	struct dirent *raw = readdir(dir);
	if (!raw)
		return NULL;

	memcpy(&local, raw, sizeof(struct dirent));

	struct qnx_dirent *new = (void *)raw;

	new->d_ino = local.d_ino;
	new->d_offset = local.d_off;
	new->d_reclen = local.d_reclen;
	new->d_namelen = strlen(local.d_name);
	strcpy(new->d_name, local.d_name);

	return new;
}
