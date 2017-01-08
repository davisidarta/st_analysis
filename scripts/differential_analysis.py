#! /usr/bin/env python
""" 
This script performs Differential
Expression Analysis using on a table with gene counts in the following format:

      GeneA   GeneB   GeneC
1x1   
1x2
...

The script can take one or several datasets.
The script also requires a file where spots are mapped
to a class for each dataset. 
This file is a tab delimited file like this:

CLASS SPOT 

The script also requires a 
list of classes/groups to perform differential expression
analysis. For example 1-2 or 1-3, etc..

The script will output the list of up-regulated and down-regulated
for each DEA comparison as well as a set of plots.

The script allows to normalize the datasets.

@Author Jose Fernandez Navarro <jose.fernandez.navarro@scilifelab.se>
"""
import argparse
import sys
import os
import numpy as np
import pandas as pd
from stanalysis.normalization import RimportLibrary
from stanalysis.visualization import scatter_plot
from stanalysis.normalization import *
from stanalysis.preprocessing import *
import rpy2.robjects.packages as rpackages
import rpy2.robjects as robjects
from rpy2.robjects import pandas2ri, r, globalenv

def get_classes_coordinate(class_file):
    """ Helper function
    to get a dictionary of spot -> class 
    from a tab delimited file
    """
    barcodes_classes = dict()
    with open(class_file, "r") as filehandler:
        for line in filehandler.readlines():
            tokens = line.split()
            assert(len(tokens) == 2)
            spot = tokens[1]
            class_label = tokens[0]
            barcodes_classes[spot] = class_label
    return barcodes_classes
   
def dea(counts, conds, size_factors=None):
    """Makes a call to DESeq2 to
    perform D.E.A. in the given
    counts matrix with the given conditions
    """
    pandas2ri.activate()
    deseq2 = RimportLibrary("DESeq2")
    r("suppressMessages(library(DESeq2))")
    # Create the R conditions and counts data
    r_counts = pandas2ri.py2ri(counts)
    cond = robjects.DataFrame({"conditions": robjects.StrVector(conds)})
    design = r('formula(~ conditions)')
    dds = r.DESeqDataSetFromMatrix(countData=r_counts, colData=cond, design=design)
    if size_factors is None:
        dds = r.DESeq(dds)
    else:
        assign_sf = r["sizeFactors<-"]
        dds = assign_sf(object=dds, value=robjects.FloatVector(size_factors))
        dds = r.estimateDispersions(dds)
        dds = r.nbinomWaldTest(dds)
    results = r.results(dds, alpha=0.05)
    results = pandas2ri.ri2py_dataframe(r['as.data.frame'](results))
    results.index = counts.index
    # Return the DESeq2 DEA results object
    pandas2ri.deactivate()
    return results
              
def main(counts_table_files, data_classes, 
         conditions_tuples, outdir, fdr, normalization):

    if len(counts_table_files) == 0 or \
    any([not os.path.isfile(f) for f in counts_table_files]):
        sys.stderr.write("Error, input file/s not present or invalid format\n")
        sys.exit(1)
        
    if len(data_classes) == 0 or \
    any([not os.path.isfile(f) for f in counts_table_files]):
        sys.stderr.write("Error, input file/s not present or invalid format\n")
        sys.exit(1)
        
    if len(data_classes) != len(counts_table_files):
        sys.stderr.write("Error, input file/s not present or invalid format\n")
        sys.exit(1)
     
    if not outdir or not os.path.isdir(outdir):
        outdir = os.getcwd()
        
    print "Output folder {}".format(outdir)
      
    # Merge input datasets (Spots are rows and genes are columns)
    counts = aggregate_datatasets(counts_table_files)
    
    # loads all the classes for the spots
    spot_classes = dict()
    for i,class_file in enumerate(data_classes):
        with open(class_file) as filehandler:
            for line in filehandler.readlines():
                tokens = line.split()
                assert(len(tokens) == 2)
                spot_classes["{}_{]".format(i,tokens[1])] = str(tokens[0])  
     
    # Normalize data
    counts = normalize_data(counts, normalization)
    
    # Genes as rows
    counts = counts.transpose()    
    
    # Iterate the conditions
    for cond in conditions_tuples:
        tokens = cond.split("-")
        assert(len(tokens) == 2)
        a = str(tokens[0])
        b = str(tokens[1])
        conds = list()
        for spot in counts.columns:
            try:
                spot_class = spot_classes[spot]
                if spot_class in [a,b]:
                    conds.append(spot_class)
                elif b == "REST":
                    conds.append(b)
                else:
                    counts.drop(spot, axis=1, inplace=True)
            except KeyError:
                counts.drop(spot, axis=1, inplace=True)
        # Make the DEA call
        print "Doing DEA for the conditions {} ...".format(cond)
        dea_results = dea(counts, conds, size_factors)
        dea_results.sort_values(by=["padj"], ascending=True, inplace=True, axis=0)
        print "Writing results to output..."
        dea_results.to_csv(os.path.join(outdir, "dea_results_{}.tsv".format(cond)), sep="\t")
        # Volcano plot
        print "Generating plots..."
        # Add colors according to differently expressed or not (needs a p-value parameter)
        colors = ["blue" if p <= fdr else "red" for p in dea_results["padj"]]
        scatter_plot(dea_results["log2FoldChange"], -np.log10(dea_results["pvalue"]),
                     xlabel="Log2FoldChange", ylabel="-log10(pvalue)", colors=colors,
                     title="Volcano plot", output=os.path.join(outdir, "volcano_{}.png".format(cond)))
                
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--counts-table-files", required=True, nargs='+', type=str,
                        help="One or more matrices with gene counts per feature/spot (genes as columns)")
    parser.add_argument("--data-classes", required=True, nargs='+', type=str,
                        help="One or more delimited file/s with the classes mapping to the spots " \
                        "(Class first column and spot second column)")
    parser.add_argument("--normalization", default="DESeq", metavar="[STR]", 
                        type=str, choices=["DESeq", "TMM", "DESeq+1", "Scran"],
                        help="Normalize the counts using:\n" \
                        "DESeq = DESeq::estimateSizeFactors()\n" \
                        "DESeq+1 = DESeq::estimateSizeFactors() + 1\n" \
                        "EdgeR = EdgeR RLE\n" \
                        "TMM = TMM with raw counts\n" \
                        "Scran = Deconvolution Sum Factors\n" \
                        "(default: %(default)s)")
    parser.add_argument("--conditions-tuples", required=True, nargs='+', type=str,
                        help="One of more tuples that represent what classes will be compared for DEA, " \
                        "for example 1-2 1-3 2-REST")
    parser.add_argument("--fdr", type=float, default=0.05,
                        help="The FDR minimum confidence threshold (default: %(default)s)")
    parser.add_argument("--outdir", help="Path to output dir")
    args = parser.parse_args()
    main(args.counts_table_files, args.data_classes, args.conditions_tuples, 
         args.outdir, args.fdr, args.normalization)