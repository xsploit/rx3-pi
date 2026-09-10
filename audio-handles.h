#ifndef RX3_AUDIO_HANDLES_H
#define RX3_AUDIO_HANDLES_H
#include "audio-recovery.h"
/* Zero-initialize once; storage must outlive every public handle. Caller
 * serializes access with pair operations. Only the pair owns bound PCMs. */
struct rx3_audio_handles {
 struct {int active;void *initial;} slot[2];
 struct rx3_audio_pair *pair;
};
enum rx3_audio_handle_state {RX3_HANDLE_UNMANAGED,RX3_HANDLE_READY,RX3_HANDLE_UNAVAILABLE,RX3_HANDLE_CLOSED};
/* Registers an already-open PCM, returning a stable public token. Duplicate
 * opens and opening during a partially closed bound pair are rejected. */
int rx3_audio_handle_open(struct rx3_audio_handles *,int output,void *pcm,void **public_handle);
/* Bind only after both registered PCMs are fully configured and pair_init
 * owns them. On failure, existing registrations remain unchanged. */
int rx3_audio_handles_bind(struct rx3_audio_handles *,struct rx3_audio_pair *);
enum rx3_audio_handle_state rx3_audio_handle_resolve(const struct rx3_audio_handles *,
 const void *public_handle,void **pcm,int *output);
/* Retire a token. A bound token stops both outputs exactly once. For an
 * unbound token, returns its real PCM in unpaired for the caller to close.
 * Returns 1 managed, 0 unmanaged, or -EBADFD already retired. */
int rx3_audio_handle_close(struct rx3_audio_handles *,const void *public_handle,void **unpaired);
#endif
