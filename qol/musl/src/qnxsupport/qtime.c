#define _GNU_SOURCE
#include <sys/time.h>

struct qnx_timeval {
	long tv_sec;
	int tv_usec;
};

static struct timeval qnx_timeval_to_linux(struct qnx_timeval t)
{
	struct timeval ret = { .tv_sec = t.tv_sec, .tv_usec = (int)t.tv_usec };

	return ret;
}

int _qnx_utimes(const char *filename, const struct qnx_timeval times[2])
{
	struct timeval t[2];

	t[0] = qnx_timeval_to_linux(times[0]);
	t[1] = qnx_timeval_to_linux(times[1]);

	return utimes(filename, t);
}

int _qnx_gettimeofday(struct qnx_timeval *when, void *not_used)
{
	struct timeval t = qnx_timeval_to_linux(*when);

	return gettimeofday(&t, not_used);
}

int _qnx_settimeofday(const struct qnx_timeval *when, void *not_used)
{
	struct timeval t = qnx_timeval_to_linux(*when);

	return settimeofday(&t, 0);
}
