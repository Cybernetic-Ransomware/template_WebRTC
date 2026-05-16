export async function getLocalStream({ audio = true, video = true } = {}) {
  return navigator.mediaDevices.getUserMedia({ audio, video });
}

export function replaceTrack(pc, newTrack) {
  const sender = pc.getSenders().find((s) => s.track?.kind === newTrack.kind);
  return sender?.replaceTrack(newTrack);
}
