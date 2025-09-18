#include <stdint.h>
#include <sys/signal.h>

typedef struct {
	uint32_t __bits[2];
} qnx_sigset_t;

#undef sa_handler
#undef sa_sigaction

struct qnx_sigaction {
	union {
		void (*sa_handler)(int);
		void (*sa_sigaction)(int, siginfo_t *, void *);
	} __sa_un;
	int sa_flags;
	qnx_sigset_t sa_mask;
};

void qnx_sigaction_to_linux(const struct qnx_sigaction *qnx_sa,
			    struct sigaction *linux_sa)
{
	linux_sa->__sa_handler.sa_handler = qnx_sa->__sa_un.sa_handler;
	linux_sa->sa_flags = qnx_sa->sa_flags;
	// copy 64 bits data
	*(uint64_t *)&(linux_sa->sa_mask) = *(uint64_t *)&(qnx_sa->sa_mask);
}

void linux_sigaction_to_qnx(const struct sigaction *linux_sa,
			    struct qnx_sigaction *qnx_sa)
{
	qnx_sa->__sa_un.sa_handler = linux_sa->__sa_handler.sa_handler;
	qnx_sa->sa_flags = linux_sa->sa_flags;
	// copy 64 bits data
	*(uint64_t *)&(qnx_sa->sa_mask) = *(uint64_t *)&(linux_sa->sa_mask);
}

int _qnx_sigaction(int signum, const struct qnx_sigaction *act,
		  struct qnx_sigaction *oldact)
{
	struct sigaction linux_act, linux_oldact;
	qnx_sigaction_to_linux(act, &linux_act);
	int ret = sigaction(signum, &linux_act, oldact ? &linux_oldact : 0);
	if (oldact)
		linux_sigaction_to_qnx(&linux_oldact, oldact);
	return ret;
}
