import hypothesis
import numpy as np

import strax
from strax.testutils import disjoint_sorted_intervals, fake_hits


@hypothesis.given(disjoint_sorted_intervals,
                  disjoint_sorted_intervals)
@hypothesis.settings(max_examples=1000, deadline=None)
def test_replace_merged(intervals, merge_instructions):
    # First we have to create some merged intervals.
    # We abuse the interval generation mechanism to create 'merge_instructions'
    # i.e. something to tell us which indices of intervals must be merged
    # together.

    merged_itvs = []
    to_remove = []
    for x in merge_instructions:
        start, end_inclusive = x['time'], x['time'] + x['length'] - 1
        if end_inclusive == start or end_inclusive >= len(intervals):
            # Pointless / invalid merge instruction
            continue
        to_remove.extend(list(range(start, end_inclusive + 1)))
        new = np.zeros(1, strax.interval_dtype)[0]
        new['time'] = intervals[start]['time']
        new['length'] = strax.endtime(intervals[end_inclusive]) - new['time']
        new['dt'] = 1
        merged_itvs.append(new)
    removed_itvs = []
    kept_itvs = []
    for i, itv in enumerate(intervals):
        if i in to_remove:
            removed_itvs.append(itv)
        else:
            kept_itvs.append(itv)

    kept_itvs = np.array(kept_itvs)
    merged_itvs = np.array(merged_itvs)

    result = strax.replace_merged(intervals, merged_itvs)
    assert len(result) == len(merged_itvs) + len(kept_itvs)
    assert np.all(np.diff(result['time']) > 0), "Not sorted"
    assert np.all(result['time'][1:] - strax.endtime(result)[:-1] >= 0), "Overlap"
    for x in kept_itvs:
        assert x in result, "Removed too many"
    for x in merged_itvs:
        assert x in result, "Didn't put in merged"
    for x in result:
        assert np.isin(x, merged_itvs) or np.isin(x, kept_itvs), "Invented itv"


@hypothesis.given(fake_hits,
                  hypothesis.strategies.integers(min_value=0, max_value=100))
@hypothesis.settings(deadline=None)
def test_add_lone_hits(hits, peak_length):
    peak = np.zeros(1, dtype=strax.peak_dtype())
    peak['length'] = peak_length
    peak['dt'] = 1

    to_pe = np.ones(10000)
    strax.add_lone_hits(peak, hits, to_pe)

    if not peak_length:
        assert peak['area'] == 0
        assert peak['data'].sum() == 0
        return

    split_hits = strax.split_by_containment(hits, peak)[0]
    dummy_peak = np.zeros(peak_length)

    for h in split_hits:
        dummy_peak[h['time']] += h['area']
    peak = peak[0]
    assert peak['area'] == np.sum(split_hits['area'])
    assert np.all(peak['data'][:peak['length']] == dummy_peak)
