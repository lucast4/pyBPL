import os
import warnings
import numpy as np

try:
    import matlab.engine
except:
    raise Exception('Must have the MATLAB Engine API for Python installed')

# start matlab engine
eng = matlab.engine.start_matlab()

try:
    # add BPL code to matlab path
    bpl_path = os.environ['BPL_PATH']
    try:
        ls_path = os.environ['LIGHTSPEED_PATH'] # for lighspeed matlab toolbox, used in BPL. see BPL readme.
        eng.addpath(eng.genpath(ls_path), nargout=0)
    except:
        pass
    eng.addpath(eng.genpath(bpl_path), nargout=0)
except:
    warnings.warn('BPL_PATH environment variable not set... therefore you'
                  'must have BPL matlab repository already added to your matlab '
                  'path')

# add current directory to matlab path
eng.addpath(os.path.dirname(__file__), nargout=0)


def generate_random_parses(I, seed=None, max_ntrials=150, max_nwalk=150,
                           max_nstroke=100, nwalk_det=5, ver="reuben", extra_junctions=None):
    # convert image to matlab format
    I = matlab.logical(I.tolist())
    # if no rng seed provided, generate one randomly
    if seed is None:
        seed = np.random.randint(1,1e6)
    
    # call matlab fn
    if ver=="reuben":
        S_walks = eng.generate_random_parses_RF(I, seed, max_ntrials, max_nwalk, max_nstroke, nwalk_det)
    elif ver=="lucas":
        if extra_junctions is not None:
            extra_junctions = matlab.int16(extra_junctions.tolist())
            S_walks, scores = eng.generate_random_parses_LT(I, seed, max_ntrials, max_nwalk, max_nstroke, nwalk_det, extra_junctions, nargout=2)
        else:
            S_walks, scores = eng.generate_random_parses_LT(I, seed, max_ntrials, max_nwalk, max_nstroke, nwalk_det, nargout=2)
    else:
        print(ver)
        assert False

    # post-process
    for i in range(len(S_walks)):
        for j in range(len(S_walks[i])):
            S_walks[i][j] = np.asarray(S_walks[i][j])

    return S_walks