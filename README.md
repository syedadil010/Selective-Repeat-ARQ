Re-implemented HTTP client and the HTTP remote file server of previous projects respectively using UDP protocol.
 Since we use UDP protocol that does not guarantee the transfer, we ensure reliability by implementing a specific
instance of the Automatic-Repeat-Request (ARQ) protocol called: Selective Repeat ARQ


# Selective-Repeat-ARQ
 
Selective Repeat is part of the automatic repeat-request (ARQ). With selective repeat, the sender sends a number of frames specified by a window size even without the need to wait for individual ACK from the receiver as in GoBack-N ARQ. The receiver may selectively reject a single frame, which may be retransmitted alone; this contrasts with other forms of ARQ, which must send every frame from that point again. The receiver accepts out-of-order frames and buffers them. The sender individually retransmits frames that have timed out.

