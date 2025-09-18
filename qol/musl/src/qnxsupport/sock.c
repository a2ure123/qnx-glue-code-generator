#include <sys/types.h>
#include <sys/socket.h>

extern int _qnx_bind(int sockfd, const struct sockaddr *addr, socklen_t addrlen);
extern int _qnx_connect(int sockfd, const struct sockaddr *addr, socklen_t addrlen);
extern void _qnx_freeaddrinfo(struct addrinfo *res);
extern int _qnx_getaddrinfo(const char *node, const char *service,
                            const struct addrinfo *hints, struct addrinfo **res);
extern struct hostent *_qnx_gethostbyname(const char *name);
extern int _qnx_getsockname(int sockfd, struct sockaddr *addr, socklen_t *addrlen);
extern int _qnx_getsockopt(int sockfd, int level, int optname,
                           void *optval, socklen_t *optlen);
extern int _qnx_listen(int sockfd, int backlog);
extern ssize_t _qnx_recv(int sockfd, void *buf, size_t len, int flags);
extern ssize_t _qnx_send(int sockfd, const void *buf, size_t len, int flags);
extern int _qnx_socket(int domain, int type, int protocol);