"""
Extract PolyA sites and cis-elements & flanking regions from PolyA_DB3

Input:
    PolyA_DB database file
    reference sequence in FASTA format (for locating hexamers)
Output:
    TSV file of PAS and hexamer intervals with all annotations in columns
"""

import re
from typing import Iterable
from typing import List
import numpy as np
import pandas as pd
import pybedtools
from pysam import FastaFile  # pylint: disable=no-name-in-module
from utr3variants.utils import extract_annotations, get_most_expressed

ANNO_COLUMN_MAP = {
    # Mapping of snakemake wildcard to column name in database
    'hexamer_motif': 'PAS Signal',
    'conservation': 'Conservation',
    'percent_expressed': 'PSE',
    'expression': 'Mean RPM',
    'most_expressed': 'most_expressed',
}


def create_signal_interval(
    feature: pybedtools.Interval, signal: str, sequence: str, name: str = None
) -> Iterable[pybedtools.Interval]:
    """
    Create pybedtools.Interval objects of signal locations within given interval

    :param feature: interval in which to search for signal
    :param signal: sequence of signal motif
    :param sequence: sequence of feature interval
    :param name: value to overwrite in feature.name if specified
    :return: generator of signal locations
    """
    name = feature.name if name is None else name
    return (
        pybedtools.Interval(
            chrom=feature.chrom,
            start=feature.end - i.end()
            if feature.strand == '-'
            else feature.start + i.start(),
            end=feature.end - i.start()
            if feature.strand == '-'
            else feature.start + i.end(),
            name=name,
            score=feature.score,
            strand=feature.strand,
        )
        for i in re.finditer(signal, sequence, re.IGNORECASE)
    )


def get_hexamers(
    feature: pybedtools.Interval, sequence: str, hexamer_column: int
) -> List[pybedtools.Interval]:
    """
    Retrieve all hexamers of regions from within given interval

    :param feature: interval with interval.name containing annotation
        of form <PAS signal>|<conservation>
    :param sequence: sequence of feature interval
    :param hexamer_column: column index of hexamer in feature name
    :return: list of hexamer coordinates
    """
    name_split = feature.name.split('|')
    hexamer_motif = name_split[hexamer_column]

    if hexamer_motif == 'NoPAS':
        return []
    if hexamer_motif == 'OtherPAS':
        signal_sequences = [
            'AGTAAA',
            'TATAAA',
            'CATAAA',
            'GATAAA',
            'AATATA',
            'AATACA',
            'AATAGA',
            'AAAAAG',
            'ACTAAA',
        ]
    elif hexamer_motif == 'Arich':
        signal_sequences = ['AAAAAA']
    else:
        signal_sequences = [hexamer_motif]
    dna_signals = [s.replace('U', 'T') for s in signal_sequences]

    hexamer_list = []
    for signal in dna_signals:
        name_split[hexamer_column] = signal  # rename hexamer annotation
        intervals = create_signal_interval(
            feature, signal, sequence, name='|'.join(name_split)
        )
        hexamer_list.extend(intervals)
    return hexamer_list


if __name__ == '__main__':
    genome = snakemake.config['assembly_ucsc']
    annotations = snakemake.params.annotations
    pas_db = snakemake.input.db.__str__()
    fasta_file = snakemake.input.fasta.__str__()
    output = snakemake.output

    print('read database')
    df = pd.read_csv(pas_db, sep='\t')

    # cleanup columns
    df['Start'] = df['Position'] - 1
    df['PSE'] = df['PSE'].str.rstrip('%').astype('float') / 100
    df['score'] = '.'

    df = get_most_expressed(
        df,
        aggregate_column='Gene Symbol',
        expression_column='Mean RPM',
        interval_columns=['Chromosome', 'Position', 'Strand'],
        new_column='most_expressed',
    )
    annotations.append('most_expressed')

    # put annotation into name
    db_cols = [ANNO_COLUMN_MAP[a] for a in annotations]
    df['Name'] = df[db_cols].astype(str).agg('|'.join, axis=1)

    # create bedtools object/table
    print('Create BedTools object')
    # BedTool object needed for hexamer extraction
    bed_cols = [
        'Chromosome',  # chrom
        'Start',  # start
        'Position',  # end
        'Name',  # name
        'score',  # score
        'Strand',  # strand
    ]
    bed = pybedtools.BedTool.from_dataframe(df[bed_cols])

    # convert back to dataframe with annotations
    intervals_df = extract_annotations(
        bed.to_dataframe(),
        annotation_string='name',
        annotation_columns=annotations,
        database='PolyA_DB',
        feature='PAS',
    )

    if 'hexamer_motif' in annotations:
        print('extract hexamers')
        bed_40nt_us = bed.slop(  # pylint: disable=unexpected-keyword-arg
            l=40, r=0, s=True, genome=genome
        ).sequence(fi=fasta_file, s=True, fullHeader=True)
        sequences = FastaFile(bed_40nt_us.seqfn)

        hexamer_intervals = []
        hex_column = annotations.index('hexamer_motif')
        for f in bed_40nt_us:
            seq = sequences.fetch(f'{f.chrom}:{f.start}-{f.stop}({f.strand})')
            hex_intervals = get_hexamers(
                feature=f, sequence=seq, hexamer_column=hex_column
            )
            hexamer_intervals.extend(hex_intervals)

        hex_df = pybedtools.BedTool(hexamer_intervals).to_dataframe()
        hex_df = extract_annotations(
            hex_df,
            annotation_string='name',
            annotation_columns=annotations,
            database='PolyA_DB',
            feature='hexamer',
        )
        intervals_df['hexamer_motif'] = np.nan
        intervals_df = pd.concat([intervals_df, hex_df])

    print('save...')
    # get stats
    intervals_df['feature'].value_counts().to_csv(output.stats, sep='\t')
    intervals_df.to_csv(output.intervals, index=False, sep='\t')
