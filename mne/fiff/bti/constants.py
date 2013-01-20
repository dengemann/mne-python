# Authors: Denis Engemann <d.engemann@fz-juelich.de?>
#
# License: BSD (3-clause)

class Bunch(dict):
    """ Container object for datasets: dictionnary-like object that
        exposes its keys as attributes.
    """

    def __init__(self, **kwargs):
        dict.__init__(self, kwargs)
        self.__dict__ = self

BTI = Bunch()

BTI.ELEC_STATE_NOT_COLLECTED           = 0
BTI.ELEC_STATE_COLLECTED               = 1
BTI.ELEC_STATE_SKIPPED                 = 2
BTI.ELEC_STATE_NOT_APPLICABLE          = 3
# 
## Byte offesets and data sizes for  different files
# 
BTI.FILE_MASK                          = 2147483647
BTI.FILE_CURPOS                        = 8
BTI.FILE_END                           = -8
   
BTI.FILE_HS_VERSION                    = 0
BTI.FILE_HS_TIMESTAMP                  = 4
BTI.FILE_HS_CHECKSUM                   = 8
BTI.FILE_HS_N_DIGPOINTS                = 12
BTI.FILE_HS_N_INDEXPOINTS              = 16
   
BTI.FILE_PDF_H_ENTER                   = 1
BTI.FILE_PDF_H_FTYPE                   = 5
BTI.FILE_PDF_H_XLABEL                  = 16
BTI.FILE_PDF_H_NEXT                    = 2
BTI.FILE_PDF_H_EXIT                    = 20
   
BTI.FILE_PDF_EPOCH_EXIT                = 28
 
BTI.FILE_PDF_CH_NEXT                   = 6
BTI.FILE_PDF_CH_LABELSIZE              = 16
BTI.FILE_PDF_CH_YLABEL                 = 16
BTI.FILE_PDF_CH_OFF_FLAG               = 16
BTI.FILE_PDF_CH_EXIT                   = 12
   
BTI.FILE_PDF_EVENT_NAME                = 16
BTI.FILE_PDF_EVENT_EXIT                = 32
   
BTI.FILE_PDF_PROCESS_BLOCKTYPE         = 20
BTI.FILE_PDF_PROCESS_USER              = 32
BTI.FILE_PDF_PROCESS_FNAME             = 256
BTI.FILE_PDF_PROCESS_EXIT              = 32
  
BTI.FILE_PDF_ASSOC_NEXT                = 32
   
BTI.FILE_PDFED_NAME                    = 17
BTI.FILE_PDFED_NEXT                    = 9
BTI.FILE_PDFED_EXIT                    = 8

#
## General data constants
#
BTI.DATA_N_IDX_POINTS          = 5
BTI.DATA_ROT_N_ROW             = 3
BTI.DATA_ROT_N_COL             = 3
BTI.DATA_XFM_N_COL             = 4
BTI.DATA_XFM_N_ROW             = 4
BTI.FIFF_LOGNO                 = 111
#
## Channel Types
#
BTI.CHTYPE_MEG       = 1
BTI.CHTYPE_EEG       = 2
BTI.CHTYPE_REFERENCE = 3
BTI.CHTYPE_EXTERNAL  = 4
BTI.CHTYPE_TRIGGER   = 5
BTI.CHTYPE_UTILITY   = 6
BTI.CHTYPE_DERIVED   = 7
BTI.CHTYPE_SHORTED   = 8
#
## User blocks
#
BTI.UB_B_MAG_INFO         = 'B_Mag_Info'
BTI.UB_B_COH_POINTS       = 'B_COH_Points'
BTI.UB_B_CCP_XFM_BLOCK    = 'b_ccp_xfm_block' 
BTI.UB_B_EEG_LOCS         = 'b_eeg_elec_locs'
BTI.UB_B_WHC_CHAN_MAP_VER = 'B_WHChanMapVer'
BTI.UB_B_WHC_CHAN_MAP     = 'B_WHChanMap'
BTI.UB_B_WHS_SUBSYS_VER   = 'B_WHSubsysVer'  # B_WHSubsysVer
BTI.UB_B_WHS_SUBSYS       = 'B_WHSubsys'
BTI.UB_B_CH_LABELS        = 'B_ch_labels'
BTI.UB_B_CALIBRATION      = 'B_Calibration'
BTI.UB_B_SYS_CONFIG_TIME  = 'B_SysConfigTime'
BTI.UB_B_DELTA_ENABLED    = 'B_DELTA_ENABLED'
BTI.UB_B_E_TABLE_USED     = 'B_E_table_used'
BTI.UB_B_E_TABLE          = 'B_E_TABLE'
BTI.UB_B_WEIGHTS_USED     = 'B_weights_used'
BTI.UB_B_TRIG_MASK        = 'B_trig_mask'
BTI.UB_B_WEIGHT_TABLE     = 'BWT_'
#
## transforms
#
BTI.T_ROT_VV = ((0, -1, 0, 0), (1, 0, 0, 0), (0, 0, 1, 0), (1, 1, 1, 1))
BTI.T_IDENT = ((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (1, 1, 1, 1))
BTI.T_ROT_IX = slice(0, 3), slice(0, 3)
BTI.T_TRANS_IX = slice(0, 3), slice(3, 4)
BTI.T_SCA_IX = slice(3, 4), slice(0, 4)