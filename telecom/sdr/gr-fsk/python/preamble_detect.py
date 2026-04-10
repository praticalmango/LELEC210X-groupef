#!/usr/bin/env python
#
# Copyright 2021 UCLouvain.
#
# This is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this software; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#


from distutils.version import LooseVersion

import numpy as np
import pmt
from gnuradio import gr

OSR_RX = 8                      # nombre d'échantillons par symbole
PREAMBLE_BITS = np.array(
    [1, 0, 1, 0, 1, 0, 1, 0,
     1, 0, 1, 0, 1, 0, 1, 0,
     1, 0, 1, 0, 1, 0, 1, 0,
     1, 0, 1, 0, 1, 0, 1, 0],
    dtype=np.int8
)
CORR_REQUIRE_PEAK = True        # True = premier pic local > seuil


# def preamble_detect_energy(y, L, threshold):
#     """
#     Preamble detection.
#     """
#     y_abs = np.abs(y)
#     for i in range(0, int(len(y) / L)):
#         sum_abs = np.sum(y_abs[i * L : (i + 1) * L])
#         if sum_abs > threshold * L:
#             return i * L + 20

#     return None

def preamble_detect_energy(y, L, threshold):
    """
    Détection de préambule CPFSK par corrélation normalisée
    sur la phase différentielle (sortie discriminateur FM).

    Signature conservée pour compatibilité GNU Radio :
        preamble_detect_energy(y, L, threshold)

    Paramètres
    ----------
    y : np.ndarray
        Signal complexe bande de base reçu, shape (N,)
    L : int
        Argument conservé pour compatibilité, non utilisé ici
    threshold : float
        Seuil de détection sur la corrélation normalisée

    Retour
    ------
    int | None
        Indice du premier échantillon juste APRÈS le préambule détecté.
        Retourne None si rien n'est détecté.
    """
    y_ = np.asarray(y)
    ylen = len(y_)

    if ylen < 2:
        return None

    if not np.iscomplexobj(y_):
        y_ = y_.astype(np.complex64) + 0j
    else:
        y_ = y_.astype(np.complex64, copy=False)

    # ------------------------------------------------------------
    # Paramètres détecteur
    # ------------------------------------------------------------
    R = int(OSR_RX)
    pre_bits = np.asarray(PREAMBLE_BITS, dtype=np.int8)[:16]
    corr_threshold = float(threshold)
    require_peak = bool(CORR_REQUIRE_PEAK)

    if R <= 0 or pre_bits.size == 0:
        return None

    # ------------------------------------------------------------
    # 1) Phase différentielle / discriminateur FM
    #    dphi[n] = angle(y[n+1] * conj(y[n]))
    # ------------------------------------------------------------
    dphi = np.angle(y_[1:] * np.conjugate(y_[:-1])).astype(np.float64)

    # Suppression du biais moyen pour limiter l'effet CFO
    dphi = dphi - np.mean(dphi)

    # ------------------------------------------------------------
    # 2) Référence dans le domaine discriminateur
    #    bit 0 -> -1, bit 1 -> +1, répété R fois
    # ------------------------------------------------------------
    ref_bits_pm = (2 * pre_bits - 1).astype(np.float64)
    ref = np.repeat(ref_bits_pm, R)

    # dphi a une longueur de 1 de moins que y
    ref = ref[:-1]

    # Suppression de la composante continue
    ref = ref - np.mean(ref)

    ref_energy = np.dot(ref, ref)
    if ref_energy <= 1e-15:
        return None

    corr_len = len(ref)   # = len(pre_bits)*R - 1

    if len(dphi) < corr_len:
        return None

    # ------------------------------------------------------------
    # 3) Corrélation glissante normalisée
    # ------------------------------------------------------------
    c_valid = np.convolve(dphi, ref[::-1], mode="valid")
    seg_energy = np.convolve(
        dphi * dphi,
        np.ones(corr_len, dtype=np.float64),
        mode="valid"
    )

    eps = 1e-12
    val_valid = np.abs(c_valid) / np.sqrt((seg_energy + eps) * (ref_energy + eps))

    # ------------------------------------------------------------
    # 4) Règle de décision
    #    - premier pic local au-dessus du seuil
    #    - sinon premier franchissement
    # ------------------------------------------------------------
    above = np.flatnonzero(val_valid >= corr_threshold)
    if above.size == 0:
        return None

    if require_peak:
        last = len(val_valid) - 1
        peaks = []

        for k in above:
            left_ok = (k == 0) or (val_valid[k] >= val_valid[k - 1])
            right_ok = (k == last) or (val_valid[k] > val_valid[k + 1])
            if left_ok and right_ok:
                peaks.append(k)

        if len(peaks) > 0:
            k_det = int(peaks[0])
        else:
            k_det = int(above[0])
    else:
        k_det = int(above[0])

    # ------------------------------------------------------------
    # 5) Convention de retour :
    #    renvoie le premier échantillon juste après le préambule
    # ------------------------------------------------------------
    first_idx = int(k_det + len(pre_bits) * R)

    if first_idx >= ylen:
        return None

    return first_idx


class preamble_detect(gr.basic_block):
    """
    docstring for block preamble_detect
    """

    def __init__(self, drate, fdev, fsamp, packet_len, threshold, enable):
        self.drate = drate
        self.fdev = fdev
        self.fsamp = fsamp
        self.packet_len = packet_len  # in bytes
        self.osr = int(fsamp / drate)
        self.threshold = threshold
        self.enable = enable

        self.filter_len = (
            8 * self.osr
        )  # Number of samples ahead that the block needs to read to output a sample
        # Remaining number of samples that go to output when the block is
        # transparent (i.e., when a preamble is detected)
        self.rem_samples = 0

        gr.basic_block.__init__(
            self,
            name="Preamble detection",
            in_sig=[np.complex64],
            out_sig=[np.complex64],
        )

        self.gr_version = gr.version()

        self.message_port_register_out(pmt.intern("SignalPow"))

    def forecast(self, noutput_items, ninputs):
        """
        Forecast is only called from a general block
        this is the default implementation
        """
        ninput_items_required = [0] * ninputs
        for i in range(ninputs):
            ninput_items_required[i] = max(
                noutput_items + self.filter_len, 2 * self.filter_len
            )

        return ninput_items_required

    def set_enable(self, enable):
        self.enable = enable

    def set_threshold(self, threshold):
        self.threshold = threshold

    def general_work(self, input_items, output_items):
        if self.rem_samples > 0:  # We are processing a previously detected packet
            N = len(output_items[0])  # available space at output
            n_out = min(self.rem_samples, N)

            # the block is transparent, i.e., all input goes to output
            self.power_est   += np.sum(np.abs(input_items[0][:n_out])**2)
            output_items[0][:n_out] = input_items[0][:n_out]
            self.consume_each(n_out)

            self.rem_samples -= n_out
            if (self.rem_samples == 0) :
                PMT_msg = pmt.from_double(self.power_est/ (8 * self.osr * (self.packet_len + 1) + self.osr))
                self.message_port_pub(pmt.intern("SignalPow"), PMT_msg)

            return n_out
        else:
            N = len(output_items[0]) - len(output_items[0]) % self.filter_len
            if self.enable == 1:
                y = input_items[0][: N + self.filter_len]
                pos = preamble_detect_energy(y, self.filter_len, self.threshold)
                self.power_est = 0

                if (
                    pos is None
                ):  # no preamble found, we discard the processed samples (no output_items)
                    self.consume_each(N)
                    return 0
                if (
                    pos > N
                ):  # in this case, n_out below is < 0. Consume samples and recompute later
                    self.consume_each(N)
                    return 0

                # A window corresponding to the length of a full packet + 1 byte + 1 symbol
                # is transferred to the output
                self.rem_samples = 8 * self.osr * (self.packet_len + 1) + self.osr

                n_out = N - pos


                self.power_est   += np.sum(np.abs(input_items[0][pos:N])**2)

                output_items[0][:n_out] = input_items[0][pos:N]
                self.consume_each(N)

                self.rem_samples -= n_out

                return n_out

            else:
                self.consume_each(N)
                return 0
