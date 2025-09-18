
dprintf *(img_alloc+0xAB), "img_alloc: malloc(%d) = %p, end: %p \n", nbytes_img, $rax, $rax+nbytes_img

# dprintf *(tiff_decode+0x95D), "malloc (%d)", $rdi
# dprintf *(tiff_decode+0x962), " = %p\n", $rax

dprintf *(tiff_decode + 0xad0), "memcpy, dst: %lx, src: %lx stride(memcpy size): %d | img->w %d | buffsize_dst %d \n", $rdi, $rsi, stride, img->w, *(int *)($rsp+0x14)

