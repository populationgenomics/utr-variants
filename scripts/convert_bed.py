import pybedtools


def convert_chr_style(
    interval: pybedtools.Interval, chr_style: str
) -> pybedtools.Interval:
    if chr_style == '' and 'chr' in interval.chrom:
        interval.chrom = interval.chrom.replace('chr', '')
    elif chr_style == 'chr' and 'chr' not in interval.chrom:
        interval.chrom = f'chr{interval.chrom}'
    return interval


if __name__ == '__main__':
    bed_intervals = pybedtools.BedTool(snakemake.input[0])
    print(f'{len(bed_intervals)} bed intervals read')

    # convert chromosome format
    bed_intervals = bed_intervals.each(
        convert_chr_style, snakemake.params['chr_style_hail']
    )

    # subset by gnomAD subset
    gnomAD_subset = snakemake.config['gnomAD']['subset']
    if gnomAD_subset:
        gnomAD_subset_interval = pybedtools.BedTool(
            gnomAD_subset.replace(':', ' ').replace('-', ' '), from_string=True
        )
        bed_intervals = bed_intervals.intersect(gnomAD_subset_interval)
        print(f'{len(bed_intervals)} bed intervals after subset')

    # convert to hail parsable string
    intervals = map(lambda x: f'{x.chrom}:{x.start + 1}-{x.stop}', bed_intervals)

    with open(snakemake.output[0], 'w') as f:
        f.writelines('\n'.join(intervals))