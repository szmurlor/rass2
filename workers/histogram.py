# -*- coding: utf-8 -*-
import logger as log
from sys import argv
import numpy as np
import re
import os
import time
import pandas as pd


def histogram(doses, markerArray, sid, scale, npts, dmax):
    start = time.time()
    d = doses[(markerArray & sid) == sid]
    if len(d) < 1:
        return (0, 0, 0)

    vol = len(d)
    hist = [(0., 100.)]
    for s in range(npts):
        treshold = dmax * (s + 1) / npts
        i = np.sum(d < treshold)
        v = 1. - (i - 1.) / vol
        hist.append(( float(scale * treshold), float(v * 100.)))

    end = time.time()
    log.debug("Histogram generated in %f seconds." % (end - start))

    return hist, float(np.min(d)), float(np.average(d)), float(np.max(d))


class DosesMain:
    def __init__(self, fname, task_log=None):
        self.path = os.path.dirname(fname)
        self.task_log = task_log

        self.override_fluences_filename = None
        self.preview_fluence = None
        self.save_png_preview_fluence = None
        self.voxels = None 
        self.x = None 
        self.xcoords = None
        self.D = None 
        self.d = None 
        self.HIST_PTS = 50

        self.init_from_m_file(fname)

    def debug(self, msg):
        log.debug(msg)

    def info(self, msg, progress=None):
        if self.task_log is not None:
            self.task_log.info(msg,progress);
        else:
            log.info(msg)

    def init_from_m_file(self, fname):
        fin = open(fname, mode='r')
        self.treatment_name = fin.readline().rstrip()
        self.bno = self.read_1_int(fin)
        self.bnos = np.array(range(self.bno), dtype=np.int32)
        self.bsizes = np.array(range(self.bno), dtype=np.int32)
        for i in range(self.bno):
            self.bnos[i], self.bsizes[i] = self.read_2_int(fin)
        self.vno = self.read_1_int(fin)
        self.dosegridscaling = float(self.read_1_float(fin))
        self.roino = self.read_1_int(fin)
        self.roinames = []
        self.roiids = []
        for i in range(self.roino):
            cols = re.split(r'\s+', fin.readline(), 1)
            self.roiids.append(int(cols[0]))
            self.roinames.append(cols[1].rstrip())
        self.btno = np.sum(self.bsizes)

    def read_fluences(self):
        res = np.zeros((self.btno,), dtype=np.float32)
        j = 0
        for i in range(self.bno):
            nbeam = self.bnos[i]
            self.info("Reading fluences for beam %s" % (nbeam))
            if self.override_fluences_filename is not None:
                fbeam = open('%s/%s%d.txt' % (self.path, self.override_fluences_filename, nbeam-1))
            else:
                fbeam = open('%s/x_%s_%d.txt' % (self.path, self.treatment_name, nbeam))
            for k in range(self.bsizes[nbeam-1]):
                s = fbeam.readline()
                cols = s.split(' ')
                if len(cols) == 1:
                    res[j] = float(cols[0])
                else:
                    res[j] = float(cols[1])
                j += 1
        return res

    def read_xcoords(self):
        res = {}
        for i in range(self.bno):
            nbeam = self.bnos[i]
            res[nbeam] = {}

            f = open('%s/xcoords_%s_%d.txt' % (self.path, self.treatment_name, nbeam))
            f.readline() # skip
            res[nbeam]["sizex"] = int(self.read_1_float(f))
            f.readline() # skip
            res[nbeam]["sizey"] = int(self.read_1_float(f))
            f.readline() # skip
            res[nbeam]["spacingx"] = self.read_1_float(f)
            f.readline() # skip
            res[nbeam]["spacingy"] = self.read_1_float(f)
            f.readline() # skip
            res[nbeam]["originx"] = self.read_1_float(f)
            f.readline() # skip
            res[nbeam]["originy"] = self.read_1_float(f)
            for k in range(self.bsizes[i]):
                x, y = self.read_2_int(f)
                res[nbeam]["%dx%d" % (x, y)] = 1

        return res

    def read_voxels(self, save_cache=False, skip_cache=False):
        fname = f'{self.path}/v_{self.treatment_name}.txt'

        fname_npy = f'{self.path}/v_{self.treatment_name}.txt.npy'
        if not skip_cache:
            if (os.path.isfile(fname_npy)):
                self.info("Reading voxel to ROI mapping from cache.")
                return np.load(fname_npy)

        self.info("Reading voxel to ROI mapping from text file. This may take a while...")
        res = pd.read_csv(fname, delimiter=" ", header=None).iloc[:,0].values
        self.info(f"Done, shape of voxels: {res.shape}")

        if save_cache:
            self.info("Saving voxel to ROI mapping to a cache file for future use.")
            np.save(fname_npy, res)

        return res
        

    def read_doses(self, save_cache=False, skip_cache=False):
        from scipy import sparse
        from scipy.sparse import dok_matrix
        fname_all = f'{self.path}/d_{self.treatment_name}.txt.npz'
        if not skip_cache:
            if os.path.isfile(fname_all):
                self.debug(f"Reading all doses from beamlets in sparse form from cache file: {fname_all}")
                self.info("Reading doses from beamlets mapping from cache file...")
                return sparse.load_npz(fname_all)

        res = dok_matrix((self.vno, self.btno),dtype=np.float32)

        start_col = 0
        for i in range(self.bno):
            nbeam = self.bnos[i]
            bsize = self.bsizes[i]

            fname = f'{self.path}/d_{self.treatment_name}_{nbeam}.txt'
            fname_npy = f'{self.path}/d_{self.treatment_name}_{nbeam}.txt.npy'

            v = None
            b = None
            d = None
            if not skip_cache:
                if os.path.isfile(fname_npy):
                    log.debug(f"Reading doses for beam no {nbeam} from cache file: {fname_npy}")
                    self.info(f"Reading doses for beam no {nbeam} from cache file.")
                    npdata = np.load(fname_npy)
                    v = npdata[:,0]
                    b = npdata[:,1]
                    d = npdata[:,2]

            if v is None:
                with open(fname) as f:
                    log.debug(f"Reading doses for beam no {nbeam} from text file: {fname}")
                    self.info(f"Reading doses for beam no {nbeam} from text file.")
                    df = pd.read_csv(f, delimiter=" ", skiprows=1, header=None)
                    v = np.array( df.iloc[:,0])
                    b = np.array( df.iloc[:,1])
                    d = np.array( df.iloc[:,2])

                    if save_cache:
                        np.save(fname_npy, df.values)

            res[v, start_col + b] = d
            start_col += bsize

        log.debug(f"Converting dok matrix to csr: {fname}")
        self.info(f"Converting all doses to csr format.")
        res = res.tocsr()
        if save_cache:
            log.debug(f"Saving csr matrix to: {fname_all}")
            self.info(f"Saving all doses mapping to cache file.")
            sparse.save_npz(fname_all, res)

        return res

    def preprocess(self):
        """Zadaniem funkcji jest przetworzenie tekstowego zbioru PARETO i zapisanie danych 
        w formacie binarnym (NumPy)"""
        main.read_voxels(save_cache=True)
        main.read_doses(save_cache=True)

    def histogram(self, gnuplot=False):
        res_hist = {
            "original": {}
        }

        if self.voxels is None:
            self.voxels = self.read_voxels(save_cache=True)

        if self.x is None:
            self.x = self.read_fluences()

        if self.D is None:
            self.D = self.read_doses(save_cache=True)

        self.info("Applying flunce vector to Dose deposition matrix to find final scaled doses...")
        self.d = self.D.dot(self.x)
        self.info("Done.")

        dmax = np.max(self.d)        
        res_hist["d_max"] = float(dmax)
        res_hist["n_pts"] = self.HIST_PTS
        res_hist["dosegridscaling"] = float(self.dosegridscaling)
        res_hist["scale"] = float(100. * self.dosegridscaling)
        res_hist["units"] = "cGy"

        interesting_rois = []
        for r in range(self.roino):
            sid = self.roiids[r]
            name = self.roinames[r]

            self.info(f"Finding histogram for ROI: {name} [sid: {sid}].")
            hist, minD, avgD, maxD = histogram(self.d, self.voxels, sid, 100. * self.dosegridscaling, self.HIST_PTS, dmax)

            if maxD > 0:
                pass
                res_hist["original"][name] = (hist, minD, avgD, maxD)

            if gnuplot and maxD > 0:
                interesting_rois.append(name)
                fname = f"{self.path}/{name}.hist"
                f = open(fname, 'w')
                for p in hist:
                    f.write('%f %f\n' % p)
                    f.close()

            self.info('Voxel doses in %20s: min=%12g avg=%12g max=%12g [cGy]' % (
                name, 100. * minD * self.dosegridscaling, 100. * avgD * self.dosegridscaling, 100. * maxD * self.dosegridscaling))

        if gnuplot:
            f = open('%s/histograms.gpt' % self.path, 'w')
            f.write('set grid\nset style data lp\nset xlabel \'Dose [cGy]\'\n'
                    'set ylabel \'% of volume\'\nset yrange [0:110]\nplot ')
            for name in interesting_rois:
                f.write('\'' + name + '.hist\', ')
            f.write('\npause 120\n')
            f.close()
        
        return res_hist

    def fluences(self):
        if self.xcoords is None:
            self.xcoords = self.read_xcoords()

        if self.x is None:
            self.x = self.read_fluences()

        t = 0
        for i in range(self.bno):

            nbeam = self.bnos[i]

            rows = self.xcoords[nbeam]["sizey"]
            cols = self.xcoords[nbeam]["sizex"]

            if self.preview_fluence or self.save_png_preview_fluence:
                fmap = np.zeros((rows, cols))

            f = open('%s/Field %d_%s.fluence' % (self.path, nbeam, self.treatment_name), 'w')
            f.write('# Pareto optimal fluence for %s field %d\n' % (self.treatment_name, nbeam))
            f.write('optimalfluence\n')
            f.write('sizex %d\n' % self.xcoords[nbeam]["sizex"])
            f.write('sizey %d\n' % self.xcoords[nbeam]["sizey"])
            f.write('spacingx  %g\n' % self.xcoords[nbeam]["spacingx"])
            f.write('spacingy  %g\n' % self.xcoords[nbeam]["spacingy"])
            f.write('originx %g\n' % self.xcoords[nbeam]["originx"])
            f.write('originy %g\n' % self.xcoords[nbeam]["originy"])
            f.write('values\n')
            for j in range(0, rows):
                for i in range(0, cols):
                    key = "%dx%d" % (j, i)
                    if key in self.xcoords[nbeam]:
                        f.write('%g\t' % self.x[t])
                    else:
                        f.write('%g\t' % 0.0)

                    if self.preview_fluence or self.save_png_preview_fluence:
                        if key in self.xcoords[nbeam]:
                            fmap[j, i] = self.x[t]

                    if key in self.xcoords[nbeam]:
                        t += 1

                f.write('\n')
            f.close()

            if self.preview_fluence:
                log.debug("Showing plot")
                import matplotlib.pyplot as plt
                plt.imshow(fmap)
                plt.show()

            if self.save_png_preview_fluence:
                fname = '%s/Preview Field %d_%s.png' % (self.path, nbeam, self.treatment_name)
                log.debug("Saving plot to %s" % fname)
                import matplotlib.pyplot as plt
                plt.imshow(fmap)
                plt.savefig(fname)

    @staticmethod
    def read_2_int(fin):
        cols = fin.readline().split()
        return int(cols[0]), int(cols[1])

    @staticmethod
    def read_3_int(fin):
        cols = fin.readline().split()
        return int(cols[0]), int(cols[1]), int(cols[2])

    @staticmethod
    def read_1_int(fin):
        cols = fin.readline().split()
        return int(cols[0])

    @staticmethod
    def read_1_float(fin):
        cols = fin.readline().split()
        return float(cols[0])


if __name__ == '__main__':
    if len(argv) < 2:
        print('Usage: %s <mainfile> [histogram|fluences] [-of override_fluences_filename] --preview_fluence --save_png_fluence' % argv[0])
        exit()

    path = os.path.dirname(argv[1])
    main = DosesMain(argv[1])

    if "-test" in argv:
        v = main.read_voxels(save_cache=True)
        print(v)
        print(np.min(v))
        print(np.max(v))

        D = main.read_doses(save_cache=True)
        print(D)
        print(D.shape)

        print("Reading fluences...")
        x = main.read_fluences()
        print("Multiplying...")
        d = D.dot(x)

        print(d)

    if "-of" in argv:
        idx = argv.index("-of")
        main.override_fluences_filename = argv[idx+1]

    if "--preview_fluence" in argv:
        print("Previewing fluences")
        main.preview_fluence = True

    if "--save_png_fluence" in argv:
        print("Saving fluences maps to png files")
        main.save_png_preview_fluence = True

    what = "."
    if len(argv) > 2 and argv[2] == "histogram":
        main.histogram()
        what = "generating histogram."

    if len(argv) > 2 and argv[2] == "fluences":
        main.fluences()
        what = "generating fluence maps."


    print("Finished %s" % what)