<script>
  import Home from './Home.svelte';
  import P2P from './modes/P2P.svelte';
  import Mesh from './modes/Mesh.svelte';
  import SFU from './modes/SFU.svelte';

  let hash = $state(location.hash);

  $effect(() => {
    const update = () => (hash = location.hash);
    window.addEventListener('hashchange', update);
    return () => window.removeEventListener('hashchange', update);
  });
</script>

{#if hash.startsWith('#/p2p')}
  <P2P />
{:else if hash.startsWith('#/mesh')}
  <Mesh />
{:else if hash.startsWith('#/sfu')}
  <SFU />
{:else}
  <Home />
{/if}
