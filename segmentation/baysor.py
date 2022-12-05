import numpy as np
import pandas as pd
import anndata

from ..resolve.resolveimage import ResolveImage

##############################
### Translate transcripts between Baysor and Resolve
##############################

def counts_resolve_to_baysor(resolvepath, baysorpath, dropgenes=[]):
    """ Transform counts from resolve format to Baysor format.
    """
    res = ResolveImage(resolvepath)
    res.full_data[["x","y","z"]] = np.round(res.full_data[["x","y","z"]]*res.voxelsize[:3],1)
    res.full_data = res.full_data[["x","y","z","GeneR"]].copy()
    res.full_data.columns = ["x","y","z","gene"]
    if len(dropgenes)>0:
        res.full_data = res.full_data[[g not in dropgenes for g in res.full_data["gene"]]]
    res.full_data.to_csv(baysorpath, index=False)

##############################
### Assign counts using only Baysor
##############################

def assign_counts_from_Baysor(countsfile, genemetafile, roikey, do_for="cell"):
    """ Assign counts to cells, using Baysor output.
    """
    if not do_for in ["cell", "cluster"]: raise ValueError("Not available")
    
    segmentation = pd.read_table(countsfile, sep=",")
    segmentation = segmentation[~segmentation["is_noise"]]
    
    var = pd.DataFrame(np.unique(segmentation["gene"]))
    var.columns = ["GeneR"]
    var.index = np.asarray(var["GeneR"])
    obs = pd.DataFrame(np.arange(segmentation[do_for].max())+1, columns=["MaskIndex"])
    obs["CellName"] = roikey+"_"+obs["MaskIndex"].astype(str)
    obs.index = np.asarray(obs["MaskIndex"])
    obs["ROI"] = roikey
    
    counts = pd.DataFrame(np.zeros((obs.shape[0],var.shape[0])),
                          columns = var.index,
                          index = obs.index)
    def count_gene(gene, segmentation, counts):
        cell = segmentation.loc[segmentation["gene"]==gene,do_for]
        u, c = np.unique(cell[cell!=0], return_counts=True)
        counts.loc[u,gene] = c
    for gene in var["GeneR"]:
        count_gene(gene, segmentation, counts)
    
    obs.index = np.asarray(obs["CellName"])
    counts.index = np.asarray(obs["CellName"])
    
    adata = anndata.AnnData(counts, dtype=np.float32, obs = obs, var = var )
    
    adata.var["Count"] = adata.X.sum(axis=0)
    genes = pd.read_excel(genemetafile).fillna("")
    genes.index = [gene.upper() if sp!="Mouse" else gene.upper()+"_M" for gene, sp in zip(genes["Gene"], genes["Species"])]
    adata.var = pd.merge(adata.var,genes,left_index=True,right_index=True,how="left")#.sort_values("Count",ascending=False)
    adata = adata[:,adata.var.sort_values("Count",ascending=False).index].copy()
    
    adata.obs["TotalGeneCount"] = counts.sum(axis=1)
    adata.obs["MouseGeneCount"] = counts[adata.var.loc[adata.var["Species"]=="Mouse","GeneR"]].sum(axis=1)
    adata.obs["HumanGeneCount"] = counts[adata.var.loc[adata.var["Species"]=="Human","GeneR"]].sum(axis=1)
    adata.obs["MouseGeneShare"] = counts[adata.var.loc[adata.var["Species"]=="Mouse","GeneR"]].sum(axis=1)/counts.sum(axis=1)
    adata.obs["HumanGeneShare"] = counts[adata.var.loc[adata.var["Species"]=="Human","GeneR"]].sum(axis=1)/counts.sum(axis=1)
    
    return adata