#include <stdint.h>
#include <sys/stat.h>

typedef uint64_t qnx_ino_t;
typedef uint64_t qnx_off_t;
typedef uint32_t qnx_dev_t;
typedef uint32_t qnx_uid_t;
typedef uint32_t qnx_gid_t;
typedef uint32_t qnx__Time32t;
typedef uint32_t qnx_mode_t;
typedef uint32_t qnx_nlink_t;
typedef uint32_t qnx_blksize_t;
typedef uint64_t qnx_blkcnt_t;

struct qnx_stat {
	qnx_ino_t st_ino;
	qnx_off_t st_size;
	qnx_dev_t st_dev;
	qnx_dev_t st_rdev;
	qnx_uid_t st_uid;
	qnx_gid_t st_gid;
	qnx__Time32t __old_st_mtime;
	qnx__Time32t __old_st_atime;
	qnx__Time32t __old_st_ctime;
	qnx_mode_t st_mode;
	qnx_nlink_t st_nlink;
	qnx_blksize_t st_blocksize;
	uint32_t st_nblocks;
	qnx_blksize_t st_blksize;
	qnx_blkcnt_t st_blocks;
	struct timespec st_mtim;
	struct timespec st_atim;
	struct timespec st_ctim;
};

static void linux_stat_to_qnx(struct stat *lstat, struct qnx_stat *qstat)
{
	qstat->st_ino = lstat->st_ino;
	qstat->st_size = lstat->st_size;
	qstat->st_dev = lstat->st_dev;
	qstat->st_rdev = lstat->st_rdev;
	qstat->st_uid = lstat->st_uid;
	qstat->st_gid = lstat->st_gid;
	qstat->__old_st_atime = lstat->st_atim.tv_sec;
	qstat->__old_st_mtime = lstat->st_mtim.tv_sec;
	qstat->__old_st_ctime = lstat->st_ctim.tv_sec;
	qstat->st_mode = lstat->st_mode;
	qstat->st_nlink = lstat->st_nlink;
	// TODO: block size is actual block size, not prefered IO size
	qstat->st_blocksize = lstat->st_blksize;
	qstat->st_nblocks = lstat->st_blocks;
	qstat->st_blksize = lstat->st_blksize;
	// TODO: blocks is computed in 512 Bytes blocks
	qstat->st_blocks = lstat->st_blocks;
	qstat->st_mtim = lstat->st_mtim;
	qstat->st_atim = lstat->st_atim;
	qstat->st_ctim = lstat->st_ctim;
}

int _qnx_stat(const char *restrict path, struct qnx_stat *restrict buf)
{
	struct stat local;
	int ret = stat(path, &local);
	if (!ret && buf)
		linux_stat_to_qnx(&local, buf);
	return ret;
}

int _qnx_lstat(const char *restrict path, struct qnx_stat *restrict buf)
{
	struct stat local;
	int ret = lstat(path, &local);
	if (!ret && buf)
		linux_stat_to_qnx(&local, buf);
	return ret;
}

int _qnx_fstat(const int fd, struct qnx_stat *restrict buf)
{
	struct stat local;
	int ret = fstat(fd, &local);
	if (!ret && buf)
		linux_stat_to_qnx(&local, buf);
	return ret;
}

int _qnx_fstatat(const int fd, const char *path, struct qnx_stat *buf,
		 int flags)
{
	struct stat local;
	int ret = fstatat(fd, path, &local, flags);
	if (!ret && buf)
		linux_stat_to_qnx(&local, buf);
	return ret;
}
