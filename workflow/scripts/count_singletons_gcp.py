"""
Count variants on GCP
    Input:
        UTR interval TSV file with all annotation columns
        gnomAD hail table
        context hail table
        mutation hail table
    Output:
        Variant count hail table

Note:
The files utr3variants/annotate_gnomad.py and utr3variants/maps.py need to be copied to
the dataproc session when running this script.
See rules/evaluation.smk for a generic hailctl command.
"""
import hail as hl

# pylint: disable=E0401
from annotate_gnomad import (
    filter_gnomad,
    annotate_for_maps,
    annotate_by_intervals,
    import_interval_table,
)
from maps import count_for_maps  # pylint: disable=E0401,E0611


def main(args):
    """
    Subset and annotate gnomAD hail table variants by intervals and count
    """
    hl.init(default_reference=args.genome_assembly)

    intervals = import_interval_table(args.intervals, 'locus_interval').persist()
    mutation_ht = hl.read_table(args.mutation_ht)
    context_ht = hl.read_table(args.context_ht)
    ht = hl.read_table(args.gnomAD_ht)

    print('Filter')
    subset_interval = hl.parse_locus_interval(args.chr_subset)
    ht = filter_gnomad(ht, [subset_interval])

    print('Annotate')
    ht = annotate_for_maps(ht, context_ht)
    for annotation in args.annotations:
        ht = annotate_by_intervals(ht, intervals, annotation_column=annotation)

    print('Count variants')
    count_ht = count_for_maps(ht, mutation_ht, additional_grouping=args.annotations)
    if args.verbose:
        count_ht.show()

    print('save...')
    count_ht.export(args.output)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Compute MAPS score')
    parser.add_argument('-o', '--output', required=True, help='Output TSV file')
    parser.add_argument(
        '--intervals',
        required=True,
        help='Comma-separate list of annotated interval bed files',
    )
    parser.add_argument(
        '--annotations',
        nargs='+',
        help='List names of annotations in --intervals file columns to include',
        required=True,
    )
    parser.add_argument(
        '--gnomAD_ht',
        required=True,
        help='Google cloud URL or directory path to gnomAD hail table',
    )
    parser.add_argument(
        '--context_ht',
        required=True,
        help='Google cloud URL or directory path to gnomAD context hail table.',
    )
    parser.add_argument(
        '--mutation_ht',
        required=True,
        help='Google cloud URL or directory path to gnomAD mutation hail table',
    )
    parser.add_argument(
        '--genome_assembly',
        required=True,
        help='Genome assembly identifier e.g. GRCh37',
    )
    parser.add_argument(
        '--chr_subset',
        required=True,
        help='Chromosome region to subset variants to',
    )
    parser.add_argument(
        '--verbose',
        required=False,
        action='store_true',
        help='Show more output',
    )
    main(args=parser.parse_args())