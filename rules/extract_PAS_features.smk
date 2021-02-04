interval_out_dir = output_root / 'intervals'

rule extract_Gencode_UTR:
    input: config["databases"]["Gencode"]["file"]
    output: interval_out_dir/'Gencode_3UTR.bed'
    shell:
        """
        zcat {input} | grep three_prime_UTR | gff2bed > {output}
        # TODO: manage chromosome style depending on gene assembly
        """

rule extract_Gencode_PAS:
    input: rules.extract_Gencode_UTR.output
    output: interval_out_dir/'Gencode_PAS.gff3'
    run:
        """
        # TODO: determine 3UTR start depending on strand
        """

rule extract_PolyA_DB:
    input:
        db=config["databases"]["PolyA_DB"]["file"],
        fasta=expand(rules.genomepy.output[0], assembly=config['assembly_ucsc'])
    output:
        PAS=interval_out_dir/'PolyA_DB_PAS.bed',
        PAS_context_40nt=interval_out_dir/'PolyA_DB_PAS_context_40nt.bed',
        PAS_context_100nt=interval_out_dir/'PolyA_DB_PAS_context_100nt.bed',
        PAS_hexamers=interval_out_dir/'PolyA_DB_PAS_hexamers.bed'
        # TODO: include basic stats
    script: '../scripts/extract_PolyA_DB.py'
