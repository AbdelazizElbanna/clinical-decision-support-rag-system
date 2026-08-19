import torch

_device = None

def get_device() -> str:
    """
    Safely determines whether to use 'cuda' or 'cpu'.
    It checks both PyTorch's visibility of CUDA and verifies whether the
    actual installed binaries support the GPU's compute capability by
    performing a minimal tensor allocation.
    """
    global _device
    if _device is not None:
        return _device
        
    if torch.cuda.is_available():
        try:
            # The P620 is compute capability 6.1
            capability = torch.cuda.get_device_capability(0)
            if capability[0] >= 6:
                # Perform a tiny allocation test to ensure the wheel actually contains compatible kernels
                _ = torch.rand(1, 1).to('cuda:0')
                _device = "cuda"
                print(f"Device validation successful: using cuda (Capability: {capability})")
            else:
                print(f"Device capability {capability} too low. Falling back to cpu.")
                _device = "cpu"
        except Exception as e:
            print(f"Warning: CUDA is available but tensor allocation failed: {e}. Falling back to cpu.")
            _device = "cpu"
    else:
        print("CUDA is not available. Using cpu.")
        _device = "cpu"
        
    return _device
