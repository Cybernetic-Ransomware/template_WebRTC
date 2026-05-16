<script>
  const modes = [
    { id: 'p2p', label: 'P2P 1:1', desc: 'Direct peer-to-peer, max 2 participants' },
    { id: 'mesh', label: 'Mesh', desc: 'Full N×N mesh, one RTCPeerConnection per peer pair' },
    {
      id: 'sfu',
      label: 'SFU',
      desc: 'Server-mediated forwarding via aiortc, one RTCPeerConnection to server',
    },
  ];
</script>

<main class="home">
  <h1>WebRTC Template</h1>
  <p class="subtitle">Three topologies, one codebase</p>
  <nav>
    {#each modes as { id, label, desc } (id)}
      <a href={`#/${id}`} class="mode-card">
        <h2>{label}</h2>
        <p>{desc}</p>
      </a>
    {/each}
  </nav>
</main>
