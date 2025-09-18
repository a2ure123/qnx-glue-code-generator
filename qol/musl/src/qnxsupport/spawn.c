#include "features.h"
#include "sys/resource.h"
#include "sys/wait.h"
#include <unistd.h>
#include <stdarg.h>
#include <stdlib.h>
#include <stdint.h>
#include <signal.h>
#include <errno.h>

#define _SIGMAX 64
#define NSIG (_SIGMAX + 1)

// clang-format off
#define POSIX_SPAWN_SETPGROUP		0x00000001	/* set process group */
#define POSIX_SPAWN_SETSIGMASK		0x00000002	/* set mask to sigmask */
#define POSIX_SPAWN_SETSIGDEF		0x00000004	/* set members of sigdefault to SIG_DFL */
#define POSIX_SPAWN_SETSCHEDULER	0x00000040	/* set members of sigignore to SIG_IGN */
#define POSIX_SPAWN_SETSCHEDPARAM	0x00000400	/* Set the scheduling policy */
#define POSIX_SPAWN_RESETIDS		0x0000

#define POSIX_SPAWN_SETSIGIGN		0x00000008	/* set members of sigignore to SIG_IGN */
#define POSIX_SPAWN_SETMPART		0x00000010	/* associate process with a set of memory partitions */
#define POSIX_SPAWN_SETSPART		0x00000020	/* associate process with a scheduler partition */
#define POSIX_SPAWN_SETND			0x00000100	/* spawn to remote node */
#define POSIX_SPAWN_EXPLICIT_CPU	0x00000800	/* Set the CPU affinity/runmask */
#define POSIX_SPAWN_SETSTACKMAX		0x00001000	/* Set the stack max */
#define POSIX_SPAWN_NOZOMBIE		0x00002000	/* Process will not zombie on death  */
#define POSIX_SPAWN_ALIGN_DEFAULT	0x00000000	/* Use system default settings for alignment */
#define POSIX_SPAWN_ALIGN_FAULT		0x01000000	/* Try to always fault data misalignment references */
#define POSIX_SPAWN_ALIGN_NOFAULT	0x02000000	/* Don't fault on misalignment, and attempt to fix it (may be slow) */

#define SPAWN_SETGROUP			POSIX_SPAWN_SETPGROUP
#define SPAWN_SETSIGMASK		POSIX_SPAWN_SETSIGMASK
#define SPAWN_SETSIGDEF			POSIX_SPAWN_SETSIGDEF
#define SPAWN_SETSIGIGN			POSIX_SPAWN_SETSIGIGN
#define SPAWN_SETMEMPART		POSIX_SPAWN_SETMPART
#define SPAWN_SETSCHEDPART		POSIX_SPAWN_SETSPART
#define SPAWN_TCSETPGROUP		0x00000080	/* Start a new terminal group */
#define SPAWN_SETND				POSIX_SPAWN_SETND
#define SPAWN_SETSID			0x00000200	/* Make new process a session leader */
#define SPAWN_EXPLICIT_SCHED	POSIX_SPAWN_SETSCHEDPARAM
#define SPAWN_EXPLICIT_CPU		POSIX_SPAWN_EXPLICIT_CPU
#define SPAWN_SETSTACKMAX		POSIX_SPAWN_SETSTACKMAX
#define SPAWN_NOZOMBIE			POSIX_SPAWN_NOZOMBIE
#define SPAWN_DEBUG				0x00004000	/* Debug process */
#define SPAWN_HOLD				0x00008000	/* Hold a process for Debug */
#define SPAWN_EXEC				0x00010000	/* Cause the spawn to act like exec() */
#define SPAWN_SEARCH_PATH		0x00020000	/* Search envar PATH for executable */
#define SPAWN_CHECK_SCRIPT		0x00040000	/* Allow starting a shell passing file as script */
#define SPAWN_ALIGN_DEFAULT		POSIX_SPAWN_ALIGN_DEFAULT
#define SPAWN_ALIGN_FAULT		POSIX_SPAWN_ALIGN_FAULT
#define SPAWN_ALIGN_NOFAULT		POSIX_SPAWN_ALIGN_NOFAULT
#define SPAWN_ALIGN_MASK		0x03000000	/* Mask for align fault states below */
#define SPAWN_PADDR64_SAFE		0x04000000	/* Memory physically located >4G is allowed */
// clang-format on

struct inheritance {
	uint32_t flags;
	pid_t pgroup;
	sigset_t sigmask;
	sigset_t sigdefault;
	sigset_t sigignore;
	uint32_t stack_max;
	int32_t policy;
	uint32_t nd;
	uint32_t runmask;
	char param[48];
};

pid_t spawn(const char *path, int fd_count, const int fd_map[],
	    const struct inheritance *inherit, char *const argv[],
	    char *const envp[])
{
	// pass the arguments to the kernel, call fork, and then call execve
	// the kernel will create a new process, and then call execve

	// create a new process
	pid_t pid;

	if (inherit->flags & SPAWN_EXEC)
		pid = 0;
	else
		pid = fork();

	if (pid != 0)
		return pid;

	// child process
	if (inherit->flags & SPAWN_SETGROUP)
		setpgid(0, inherit->pgroup);
	if (inherit->flags & SPAWN_SETSIGMASK)
		sigprocmask(SIG_SETMASK, &inherit->sigmask, 0);
	if (inherit->flags & SPAWN_SETSID)
		setsid();
	if (inherit->flags & SPAWN_SETSTACKMAX)
		setrlimit(RLIMIT_STACK, &(struct rlimit){ inherit->stack_max,
							  RLIM_INFINITY });

	if (inherit->flags & SPAWN_SETSIGDEF)
		for (int i = 1; i < NSIG; i++)
			if (sigismember(&inherit->sigdefault, i))
				signal(i, SIG_DFL);
	if (inherit->flags & SPAWN_SETSIGIGN)
		for (int i = 1; i < NSIG; i++)
			if (sigismember(&inherit->sigignore, i))
				signal(i, SIG_IGN);

	// keep fd
	for (int i = 0; i < fd_count; i++) {
		if (fd_map[i] != i) {
			dup2(fd_map[i], i);
			close(fd_map[i]);
		}
	}

	// call execve
	execve(path, argv, envp);

	// will not reach here
}

#define DOIT_CVT_L2V(arg0, argv, envv_assignment)                     \
	do {                                                          \
		va_list ap;                                           \
		unsigned num;                                         \
		char **p;                                             \
                                                                      \
		num = 1;                                              \
		if (arg0 != 0) {                                      \
			va_start(ap, arg0);                           \
			for (++num; va_arg(ap, char *); num++) {      \
				/* nothing to do */                   \
			}                                             \
			va_end(ap);                                   \
		}                                                     \
                                                                      \
		if (!(argv = __builtin_alloca(num * sizeof *argv))) { \
			errno = ENOMEM;                               \
			return -1;                                    \
		}                                                     \
                                                                      \
		p = argv;                                             \
		*p++ = (char *)arg0;                                  \
		va_start(ap, arg0);                                   \
		if (arg0 != 0) {                                      \
			while ((*p++ = va_arg(ap, char *))) {         \
				/* nothing to do */                   \
			}                                             \
		}                                                     \
		(envv_assignment);                                    \
		va_end(ap);                                           \
	} while (0)

#define CVT_L2V(arg0, argv) DOIT_CVT_L2V(arg0, argv, num = 1)

#define CVT_L2V_ENV(arg0, argv, envv) \
	DOIT_CVT_L2V(arg0, argv, envv = va_arg(ap, char **))

#define P_WAIT 0
#define P_NOWAIT 1
#define P_OVERLAY 2
#define P_NOWAITO 3

int spawnve(int mode, const char *path, char *const argv[], char *const envp[])
{
	pid_t pid;
	struct inheritance attr;

	switch (mode) {
	case P_WAIT:
	case P_NOWAIT:
		attr.flags = 0;
		break;

	case P_OVERLAY:
		attr.flags = SPAWN_EXEC;
		break;

	case P_NOWAITO:
		attr.flags = SPAWN_NOZOMBIE;
		break;

	default:
		errno = EINVAL;
		return -1;
	}

	if ((pid = spawn(path, 0, 0, &attr, argv, envp)) != -1) {
		if (mode == P_WAIT) {
			if (waitpid(pid, &pid, 0) == -1) {
				return -1;
			}
		}
	}

	return pid;
}

weak_alias(spawnve, spawnvpe);

int spawnv(int mode, const char *path, char *const argv[])
{
	return spawnve(mode, path, argv, 0);
}

weak_alias(spawnv, spawnvp);

int spawnl(int mode, const char *path, const char *arg0, ...)
{
	char **argv;

	CVT_L2V(arg0, argv);
	return spawnve(mode, path, argv, 0);
}

weak_alias(spawnl, spawnlp);

int spawnle(int mode, const char *path, const char *arg0, ...)
{
	char **argv;
	char **envv;

	CVT_L2V_ENV(arg0, argv, envv);
	return spawnve(mode, path, argv, envv);
}
weak_alias(spawnle, spawnlpe);
