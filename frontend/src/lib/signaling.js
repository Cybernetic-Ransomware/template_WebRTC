export class SignalingClient {
  #ws;
  #handlers;
  #decoder = new TextDecoder();
  #TYPES = {
    'room-info': 'onRoomInfo',
    'peer-joined': 'onPeerJoined',
    'peer-left': 'onPeerLeft',
    offer: 'onOffer',
    answer: 'onAnswer',
    'ice-candidate': 'onIceCandidate',
  };

  constructor(url, handlers = {}) {
    this.#handlers = handlers;
    this.#ws = new WebSocket(url);
    this.#ws.binaryType = 'arraybuffer';
    this.#ws.onopen = () => handlers.onOpen?.();
    this.#ws.onmessage = (event) => this.#onMessage(event);
    this.#ws.onerror = (e) => handlers.onError?.(e);
    this.#ws.onclose = (e) => handlers.onClose?.(e);
  }

  #onMessage(event) {
    const text = this.#decoder.decode(event.data);
    const msg = JSON.parse(text);
    this.#handlers[this.#TYPES[msg.type]]?.(msg);
  }

  send(message) {
    if (this.#ws.readyState === WebSocket.OPEN) {
      this.#ws.send(JSON.stringify(message));
    }
  }

  close() {
    this.#ws.close();
  }
}
