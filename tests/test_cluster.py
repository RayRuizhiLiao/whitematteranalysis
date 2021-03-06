#!/usr/bin/env python

import whitematteranalysis as wma
import vtk
import numpy
import matplotlib.pyplot as plt
import multiprocessing
import glob
import sys
import os

number_of_jobs = multiprocessing.cpu_count()
print 'CPUs detected:', number_of_jobs

# these are small with only 500 fibers each
input_directory = 'test_data'
outdir = 'test_cluster_results'

# parameters for clustering creation
number_of_clusters = 20
#number_of_fibers_per_subject = 3000
number_of_fibers_per_subject = 500
fiber_length = 40
number_of_sampled_fibers = 500
number_of_eigenvectors = 15
sigma = 50

# read and process input
print 'Read and preprocess'
input_pds, subject_ids = wma.io.read_and_preprocess_polydata_directory(input_directory, fiber_length, number_of_fibers_per_subject)

number_of_subjects = len(subject_ids)

# append input data into one object
appender = vtk.vtkAppendPolyData()
for pd in input_pds:
    if (vtk.vtkVersion().GetVTKMajorVersion() >= 6.0):
        appender.AddInputData(pd)
    else:
        appender.AddInput(pd)

appender.Update()
input_data = appender.GetOutput()

del input_pds

# CLUSTERING step
nystrom_mask = numpy.random.permutation(input_data.GetNumberOfLines()) < number_of_sampled_fibers

output_polydata_s, cluster_numbers_s, color, embed, distortion, atlas = \
    wma.cluster.spectral(input_data, number_of_clusters=number_of_clusters, \
                             number_of_jobs=number_of_jobs, use_nystrom=True, \
                             nystrom_mask = nystrom_mask, \
                             number_of_eigenvectors = number_of_eigenvectors, \
                             sigma = sigma)


# OUTPUT information
print 'View results'
if not os.path.isdir(outdir):
    os.mkdir(outdir)

# view the whole thing
print 'Rendering and saving image'
ren = wma.render.render(output_polydata_s, 500)
ren.save_views(outdir)
del ren

# View cluster distribution
print 'Saving cluster histogram'
plt.figure()
plt.hist(cluster_numbers_s, number_of_clusters)
plt.savefig(os.path.join(outdir,'cluster_hist.pdf'))
plt.close()

# view cluster numbers
output_polydata_s.GetCellData().SetActiveScalars('ClusterNumber')
ren = wma.render.render(output_polydata_s)
directory = os.path.join(outdir, 'atlas_clusters') 
if not os.path.isdir(directory):
    os.mkdir(directory)
ren.save_views(directory)
del ren

# compute distances to centroids
diff = atlas.centroids[cluster_numbers_s] - embed
centroid_distance = numpy.sum(numpy.multiply(diff,diff), 1)

fiber_mask = centroid_distance > 15.0
pd_dist = wma.filter.mask(output_polydata_s, fiber_mask, centroid_distance)
ren_dmax = wma.render.render(pd_dist, 1000)
plt.hist(centroid_distance,1000);
plt.savefig( os.path.join(outdir, 'centroid_distances.pdf'))
directory = os.path.join(outdir, 'max_dist') 
if not os.path.isdir(directory):
    os.mkdir(directory)
ren_dmax.save_views(directory)
del ren_dmax

fiber_mask = centroid_distance < 5.0
pd_dist = wma.filter.mask(output_polydata_s, fiber_mask, centroid_distance)
ren_dmin = wma.render.render(pd_dist, 1000)
directory = os.path.join(outdir, 'min_dist') 
if not os.path.isdir(directory):
    os.mkdir(directory)
ren_dmin.save_views(directory)
del ren_dmin

# figure out which subject each fiber was from 
subject_fiber_list = list()
for sidx in range(number_of_subjects):
    for fidx in range(number_of_fibers_per_subject):
        subject_fiber_list.append(sidx)
subject_fiber_list = numpy.array(subject_fiber_list)

# figure out how many subjects in most clusters
subjects_per_cluster = list()
for cidx in range(atlas.centroids.shape[0]):
    cluster_mask = (cluster_numbers_s==cidx) 
    subjects_per_cluster.append(len(set(subject_fiber_list[cluster_mask])))

plt.figure()
plt.hist(subjects_per_cluster, number_of_subjects)
plt.savefig( os.path.join(outdir, 'subjects_per_cluster_hist.pdf'))
plt.close()

