from webrtc_template.modes.mesh import handle as handle_mesh
from webrtc_template.modes.p2p import handle as handle_p2p
from webrtc_template.modes.sfu import handle as handle_sfu

MODE_HANDLERS = {
    "p2p": handle_p2p,
    "mesh": handle_mesh,
    "sfu": handle_sfu,
}
