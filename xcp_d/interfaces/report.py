# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""Interfaces to generate reportlets."""

import os
import time
import re
import pandas as pd

from nipype.interfaces.base import (
    traits, TraitedSpec, BaseInterfaceInputSpec,
    File, InputMultiObject, Str, isdefined,
    SimpleInterface)


SUBJECT_TEMPLATE = """\
\t<ul class="elem-desc">
\t\t<li>Subject ID: {subject_id}</li>
\t\t<li>BOLD series: {num_bold:d}</li>
\t</ul>
"""

QC_TEMPLATE = """\t\t<h3 class="elem-title">Summary</h3>
\t\t<ul class="elem-desc">
\t\t\t<li>BOLD volume space: {space}s</li>
\t\t\t<li>Repetition Time (TR): {tr:.03g}s</li>
\t\t\t<li>Mean Framewise Displacement: {meanFD}</li>
\t\t\t<li>Mean Relative RMS Motion: {meanRMS}</li>
\t\t\t<li>Max Relative RMS Motion: {maxRMS}</li>
\t\t\t<li>DVARS Before and After Processing : {dvarsbfaf}</li>
\t\t\t<li>Correlation between DVARS and FD  Before and After Processing : {corrfddv}</li>
\t\t\t<li>Number of Volumes Censored : {volcensored}</li>
\t\t</ul>
"""

ABOUT_TEMPLATE = """\t<ul>
\t\t<li>xcp_d version: {version}</li>
\t\t<li>xcp_d: <code>{command}</code></li>
\t\t<li>xcp_d preprocessed: {date}</li>
\t</ul>
</div>
"""


class SummaryOutputSpec(TraitedSpec):
    out_report = File(exists=True, desc='HTML segment containing summary')


class SummaryInterface(SimpleInterface):
    output_spec = SummaryOutputSpec

    def _run_interface(self, runtime):
        segment = self._generate_segment()
        fname = os.path.join(runtime.cwd, 'report.html')
        with open(fname, 'w') as fobj:
            fobj.write(segment)
        self._results['out_report'] = fname
        return runtime

    def _generate_segment(self):
        raise NotImplementedError


class SubjectSummaryInputSpec(BaseInterfaceInputSpec):
    subject_id = Str(desc='Subject ID')
    bold = InputMultiObject(traits.Either(
        File(exists=True), traits.List(File(exists=True))),
        desc='BOLD or CIFTI functional series')

class SubjectSummaryOutputSpec(SummaryOutputSpec):
    # This exists to ensure that the summary is run prior to the first ReconAll
    # call, allowing a determination whether there is a pre-existing directory
    subject_id = Str(desc='subject ID')

class SubjectSummary(SummaryInterface):
    input_spec = SubjectSummaryInputSpec
    output_spec = SubjectSummaryOutputSpec

    def _run_interface(self, runtime):
        if isdefined(self.inputs.subject_id):
            self._results['subject_id'] = self.inputs.subject_id
        return super(SubjectSummary, self)._run_interface(runtime)

    def _generate_segment(self):
        # Add list of tasks with number of runs
        num_bold = len(self.inputs.bold)
         
        


        return SUBJECT_TEMPLATE.format(
            subject_id = self.inputs.subject_id,
            num_bold = num_bold)


class FunctionalSummaryInputSpec(BaseInterfaceInputSpec):
    bold_file = traits.File(True, True, desc='cifti or bold File')
    qc_file = traits.File(exists=True, desc='qc file')
    tr = traits.Float(mandatory=True,desc='Repetition time', )


class FunctionalSummary(SummaryInterface):
    input_spec = FunctionalSummaryInputSpec

    def _generate_segment(self):
        space = get_space (self.inputs.bold_file)
        tr = self.inputs.tr
        qcfile = pd.read_csv(self.inputs.qc_file)
        meanFD = "{} ".format(round(qcfile['meanFD'][0], 4))
        meanRMS = " {} ".format(round(qcfile['relMeansRMSMotion'][0], 4))
        maxRMS =" {} ".format(round(qcfile['relMaxRMSMotion'][0], 4))
        dvars = "  {},{} " .format(
                    round(qcfile['meanDVInit'][0], 4), round(qcfile['meanDVFinal'][0], 4))
        fddvars = " {},  {} " .format(
                    round(qcfile['motionDVCorrInit'][0], 4),
                            round(qcfile['motionDVCorrFinal'][0], 4))
        nvolcen = " {} ".format(round(qcfile['nVolCensored'][0], 4))
        

        return QC_TEMPLATE.format(
            space =space, tr=tr, meanFD = meanFD,  meanRMS = meanRMS, maxRMS = maxRMS, 
            dvarsbfaf = dvars, corrfddv= fddvars, volcensored = nvolcen
            )


class AboutSummaryInputSpec(BaseInterfaceInputSpec):
    version = Str(desc='xcp_d version')
    command = Str(desc='xcp_d command')
    # Date not included - update timestamp only if version or command changes


class AboutSummary(SummaryInterface):
    input_spec = AboutSummaryInputSpec

    def _generate_segment(self):
        return ABOUT_TEMPLATE.format(version=self.inputs.version,
                                     command=self.inputs.command,
                                     date=time.strftime("%Y-%m-%d %H:%M:%S %z"))



def get_space(bold_file):
    """
     extract space from bold/cifti
    """
    bbfile = os.path.basename(bold_file)
    if bbfile.endswith('.dtseries.nii'):
        return 'fsLR'
    else:
        if 'space'not in bbfile:
            return 'native'
        elif 'space' in bbfile:
            bbfileS = bbfile.split('_')
            
            for j in bbfileS:
                if 'space' in j:
                    return j.split('-')[1]
    