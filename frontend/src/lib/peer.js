export function createPeerConnection(iceServers, onIceCandidate) {
  const pc = new RTCPeerConnection({ iceServers });
  pc.onicecandidate = ({ candidate }) => {
    if (candidate !== null) onIceCandidate(candidate.toJSON());
  };
  return pc;
}
