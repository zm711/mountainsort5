from typing import Dict, Union
import numpy as np
import spikeinterface as si
from .Scheme3SortingParameters import Scheme3SortingParameters
from .sorting_scheme2 import get_time_chunks
from .sorting_scheme2 import sorting_scheme2, get_times_labels_from_sorting
from ..core.get_block_recording_for_scheme3 import get_block_recording_for_scheme3
from ..core.SnippetClassifier import SnippetClassifier


def sorting_scheme3(
    recording: si.BaseRecording, *,
    sorting_parameters: Scheme3SortingParameters
) -> si.BaseSorting:
    """MountainSort 5 sorting scheme 3

    Args:
        recording (si.BaseRecording): SpikeInterface recording object
        sorting_parameters (Scheme3SortingParameters): Sorting parameters

    Returns:
        si.BaseSorting: SpikeInterface sorting object
    """
    M = recording.get_num_channels()
    N = recording.get_num_frames()
    sampling_frequency = recording.sampling_frequency
    channel_locations = recording.get_channel_locations()

    sorting_parameters.check_valid(M=M, N=N, sampling_frequency=sampling_frequency, channel_locations=channel_locations)

    chunk_size = int(sorting_parameters.block_duration_sec * sampling_frequency) # size of chunks in samples
    chunks = get_time_chunks(recording.get_num_samples(), chunk_size=chunk_size, padding=1000)

    times_list: list[np.ndarray] = []
    labels_list: list[np.ndarray] = []
    last_label_used = 0
    previous_snippet_classifiers: Union[Dict[int, SnippetClassifier], None] = None
    for i, chunk in enumerate(chunks):
        print('')
        print('=============================================')
        print(f'Processing block {i + 1} of {len(chunks)}...')
        subrecording = get_block_recording_for_scheme3(recording=recording, start_frame=chunk.start - chunk.padding_left, end_frame=chunk.end + chunk.padding_right)
        subsorting, snippet_classifiers = sorting_scheme2(
            subrecording,
            sorting_parameters=sorting_parameters.block_sorting_parameters,
            return_snippet_classifiers=True,
            reference_snippet_classifiers=previous_snippet_classifiers,
            label_offset=last_label_used
        )
        previous_snippet_classifiers = snippet_classifiers
        times0, labels0 = get_times_labels_from_sorting(subsorting)
        valid_inds = np.where((times0 >= chunk.padding_left) & (times0 < chunk.padding_left + chunk.end - chunk.start))[0]
        times0 = times0[valid_inds]
        labels0 = labels0[valid_inds]
        times0 = times0 + chunk.start - chunk.padding_left
        if len(labels0) > 0:
            last_label_used = max(last_label_used, np.max(labels0))
        times_list.append(times0)
        labels_list.append(labels0)
    
    times_concat = np.concatenate(times_list)
    labels_concat = np.concatenate(labels_list)

    # Now create a new sorting object from the times and labels results
    sorting2 = si.NumpySorting.from_times_labels([times_concat], [labels_concat], sampling_frequency=recording.sampling_frequency)

    return sorting2