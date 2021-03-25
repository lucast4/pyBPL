% Mostly bottom-up method for generating a set
% See https://github.com/brendenlake/BPL/blob/master/bottomup/generate_random_parses.m
function [S_walks, score_sorted] = generate_random_parses_LT(I,seed,max_ntrials,max_nwalk,max_nstroke,nwalk_det,extra_junctions)
    % LT:
    % extra_junctions, array N x 2, are N points that would like to add as junctions.
    % get_substrokes, if true, then does substroke search, which implemnets BPL prior knowledge
    get_substrokes = false;

    if ~exist('extra_junctions', 'var')
        extra_junctions = [];
    end
    
    % apply random seed
    if exist('seed', 'var')
        rng(seed);
    end

    % load library
    ps = defaultps; load(ps.libname,'lib');

    % load default parameters
    ps = defaultps_bottomup;
    if ~exist('max_ntrials', 'var')
        max_ntrials = ps.max_nwalk;
    end
    if ~exist('max_nwalk', 'var')
        max_nwalk = ps.max_nwalk;
    end
    if ~exist('max_nstroke', 'var')
        max_nstroke = ps.max_nstroke;
    end
    if ~exist('nwalk_det', 'var')
        nwalk_det = ps.nwalk_det;
    end

    % Check that image is in the right format    
    assert(UtilImage.check_black_is_true(I));
    
    % If we have a blank image
    if sum(sum(I))==0
       bestMP = [];
       return
    end
    
    % Get character skeleton from the fast bottom-up method
    if false
        G = extract_skeleton(I);
    else
        G = extract_skeleton_LT(I, extra_junctions);
    end

    % Create a set of random parses through random walks
    RW = RandomWalker(G);
    if get_substrokes
        % Original BPL version, does parse into substrokes
        PP = ProcessParses(I,lib,false);
    else
        % Reuben version, does not parse into substrokes
        PP = ProcessParsesRF(I,lib,false);
    end
    
    % Add deterministic minimum angle walks
    for i=1:nwalk_det
        PP.add(RW.det_walk);
    end
    
    % Sample random walks until we reach capacity.
    ntrials = PP.nwalks;
    while (PP.nl < max_nstroke) && (PP.nwalks < max_nwalk) && (ntrials < max_ntrials)
        list_walks = RW.sample(1);
        PP.add(list_walks{1});
        ntrials = ntrials + 1;
    end

    % test, just print to see structure of strokes/substrokes
    % PP.freeze;
    % S_walks = PP.get_S;
    % for i=1:length(S_walks)
    %     disp(i)
    %     disp(S_walks{i})
    % end
    % assert(false)

    % flatten hierarchical programs (strokes --> substrokes) into list of strokes, where
    % substrokes are now considered strokes now
    if get_substrokes
        PP.freeze;
        S_walks = PP.get_S;
        % disp(S_walks{8})
        % assert(false)
        strokes = cell(length(S_walks), 1);
        for i=1:length(S_walks)
            % Flatten all substrokes into list of strokes
            strokes_not_flattened = S_walks{i};
            for j=1:length(strokes_not_flattened)
                % disp(strokes_not_flattened{j})
                for jj=1:length(strokes_not_flattened{j})
                    strokes{i}{end+1} = strokes_not_flattened{j}{jj};
                end
            end
            % disp(i)
            % disp(strokes{i})
        end
        S_walks = strokes;
    else
        PP.freeze;
        S_walks = PP.get_S;
    end
    score_sorted = zeros(length(S_walks), 1);


    % If want to apply original BPL code to further parse into motor programs...
    if false % Get motor program, which means can get substrokes.
        ninit = 20 % number best progrmas to take
        verbose = true

        % only optimizes by image score; original version also uses other prior scores.
        [bestMP, score_sorted] = parses_to_MPs_nooptimize(I,PP,ninit,lib,verbose); 

        % flatten motor programs into lists of strokes
        strokes = cell(length(bestMP), 1)
        for i=1:length(bestMP)
            % disp(i)
            % disp(bestMP{i}.motor)
            % Flatten all substrokes into list of strokes
            strokes_not_flattened = bestMP{i}.motor;
            for j=1:length(strokes_not_flattened)
                % disp(strokes_not_flattened{j})
                for jj=1:length(strokes_not_flattened{j})
                    strokes{i}{end+1} = strokes_not_flattened{j}{jj}
                end
            end
            % disp(i)
            % disp(strokes{i})
        end
        S_walks = strokes;
    end

end