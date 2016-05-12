#!/usr/bin/python
# -*- coding: utf8 -*-

"""
This demo demonstrates how to embed a matplotlib (mpl) plot 
into a PyQt4 GUI application, including:
* Using the navigation toolbar
* Adding data to the plot
* Dynamically modifying the plot's properties
* Processing mpl events
* Saving the plot to a file from a menu
The main goal is to serve as a basis for developing rich PyQt GUI
applications featuring mpl plots (using the mpl OO API).
Eli Bendersky (eliben@gmail.com)
License: this code is in the public domain
Last modified: 19.01.2009
"""
import sys, os, random
from PyQt4.QtCore import *
from PyQt4.QtGui import *

import numpy as np
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar
#from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import matplotlib

def helptext():
    print """
    Description:
    ------------
    This python scripts parses fort.21 retrieving the informaition about the 
    transitions and plot them using matplotlib. An interactive plot is generated
    which allow the used to assign the stick transition by clicking on them.
    The script can also export the plot to xmgrace format.
    
    Instructions:
    ------------
    * Interacting with the plot:
      -Get info from a transition: right-mouse-click on a stick
      -Set the next/previous indexed transiton: +/- keys
      -Place a label: left-mouse-click on a stick
      -Move a label: hold the label with the left-mouse-button
      -Remove one label: on the label, right-mouse-click
      -Deactivate a class: mouse-click on the legend
      -Clean info about transitons: left-mouse-click on the title
      -Clean all labels: right-mouse-click on the title
      -Export to xmgrace: central-mouse-click on the title
    
    * Command line flags
      By default the script plots the transitions for all classes in absolute intensity
      but this behaviour can be tuned with command line flags
      
       Flag      Action
      ---------------------
       -fc       Plot FCfactors
       -fc-abs   Plot absolute value of FCfactors
       -fc-sqr   Plot square values of FCfactors
       -maxC     Maximum Class to show
       -v        Print version info and quit
       -h        This help
       
    """

class spectral_transition:
    """
    A class for spectral transitions
    """
    def __init__(self):
        self.motherstate = 0
        self.fcclass = 0
        self.position = 0.0
        self.fcfactor = 0.0
        self.intensity = 0.0
        self.einit = 0.0
        self.efin = 0.0
        self.DE = 0.0
        self.DE00cm = 0.0
        self.init = [0]
        self.final = [0]
        self.qinit = [0]
        self.qfinal = [0]
        self.index = 0
        
    def def_transitions(self):
        #DEFINE TRANSITIONS
        #initial modes
        modesI=''
        for i in range(0,self.init.count(0)):
            self.init.remove(0)
        if len(self.init) > 0:
            for i in range(0,len(self.init)):
                modesI = modesI+str(self.init[i])+'('+str(self.qinit[i])+'),'
            #Remove trailing comma
            modesI = modesI[0:-1]
        else:
            modesI = '0'
        #final modes
        modesF=''
        for i in range(0,self.final.count(0)):
            self.final.remove(0)
        if len(self.final) > 0:
            for i in range(0,len(self.final)):
                modesF = modesF+str(self.final[i])+'('+str(self.qfinal[i])+'),'
            #Remove trailing comma
            modesF = modesF[0:-1]
        else:
            modesF = '0'
        #Define attribute transition
        return modesI+" --> "+modesF
    
    def info(self):
        transition = self.def_transitions()
        msg = """ Transition:   \t%s 
  =========================
  MotherState:\t%s
  FC class:     \t%s 
  Einit(eV):    \t%s 
  Efin (eV):    \t%s 
  DE   (eV):    \t%s 
  Intensity:    \t%s 
  FCfactor:     \t%s 
  INDEX:        \t%s
        """%(transition,
             self.motherstate,
             self.fcclass,
             self.einit,
             self.efin,
             self.DE,
             self.intensity,
             self.fcfactor,
             self.index)
        return msg

class AppForm(QMainWindow):
    def __init__(self, parent=None):
        """
        The _init__ function takes care of:
        1) Building the app window 
        2) Load data (fort.21, fort.22)
        3) Initialize some variables
        """
        QMainWindow.__init__(self, parent)
        self.setWindowTitle('FCclasses analyzer')

        self.create_menu()
        self.create_main_frame()
        self.create_status_bar()

        # Initialize additional items
        # Broadening info
        self.broadening="Gau"
        self.update_hwhm_from_slider(UpdateConvolute=False)
        # Data type
        self.data_type ="Intensity"
        # Line markers
        self.selected  = self.axes.vlines([0.0], [0.0], [0.0], linewidths=3,
                         color='yellow', visible=False)
        # Label dictionary
        self.labs = dict()
        self.active_label = None
        self.active_tr = None
        self.spectrum_exp = None
        self.spectrum_sim = None
        
        # Get command line arguments
        cml_args = get_args()
        MaxClass = cml_args.get("-maxC")
        MaxClass = int(MaxClass)
        self.spc_type = cml_args.get("-type")
        self.spc_type = self.spc_type.lower()
        # Data load
        self.fcclass_list = read_fort21(MaxClass)
        for i,tr in enumerate(self.fcclass_list):
            print "Class %s. Size: %s"%(i,len(tr))
        print ""
        self.xbin,self.ybin = read_spc_xy('fort.22')
        self.xbin = np.array(self.xbin)
        self.ybin = np.array(self.ybin)
        
        # This is the load driver
        self.load_sticks()
        self.load_sticks_legend()
        self.load_convoluted()
        
        
    #==========================================================
    # FUNCTIONS CONNECTED WITH THE MENU OPTIONS
    #==========================================================
    def save_plot(self):
        file_choices = "PNG (*.png)|*.png"
        
        path = unicode(QFileDialog.getSaveFileName(self, 
                        'Save file', '', 
                        file_choices))
        if path:
            self.canvas.print_figure(path, dpi=self.dpi)
            self.statusBar().showMessage('Saved to %s' % path, 2000)
            
    def open_plot(self):
        file_choices = r"Data file (*.dat) (*.dat);; All files (*)"
        
        path = unicode(QFileDialog.getOpenFileName(self, 
                        'Open spectrum', '', 
                        file_choices))
        if path:
            self.statusBar().showMessage('Opened %s' % path, 2000)    
            x,y = read_spc_xy(path)
            x = np.array(x)
            y = np.array(y)
            # Pop-up a selector to indicate units of Xaxis
            ok, units = self.spc_import_assitant_Xaxis()
            if not ok:
                self.statusBar().showMessage('Load data aborted', 2000)
                return
            # Transform X axis if needed
            if units == "cm^-1":
                x = x / 1.23981e-4
            elif units == "nm":
                x = 1239.81/x
                
            # Pop-up a selector to indicate units of Yaxis
            ok, data_type = self.spc_import_assitant_Yaxis()
            if not ok:
                self.statusBar().showMessage('Load data aborted', 2000)
                return
                
            self.load_experiment_spc(x,y)


    def spc_import_assitant_Xaxis(self):
        unit_list = ("eV", "cm^-1", "nm")
                 
        units, ok = QInputDialog.getItem(self, "X axis selection", 
                    "X-Units", unit_list, 0, False)
                         
        if not ok or not units:
            units = ""
        
        return ok, units
        
        
    def spc_import_assitant_Yaxis(self):
        data_type_list = ("Intensity","Lineshape")
                 
        data_type, ok = QInputDialog.getItem(self, "Y axis selection", 
                            "Data type", data_type_list, 0, False)
                         
        if not ok or not data_type:
            data_type = ""
                
        return ok, data_type
        
            
    def xmgr_export(self):
        file_choices = "xmgrace graph (*.agr) (*.agr);; All files (*)"
        
        path = unicode(QFileDialog.getSaveFileName(self, 
                        'Export to file', '', 
                        file_choices))
        if path:
            export_xmgrace(path,self.axes,self.fcclass_list,self.spectrum_sim[0],self.labs)
    
    def on_about(self):
        msg = """ 
       A python application to analyze FCclasses TI spectra
       J.Cerezo, May 2016
        
       SHORT INSTRUCTIONS:
         -Get info from a transition: right-mouse-click on a stick
         -Set the next/previous indexed transiton: +/- keys
         -Place a label: left-mouse-click on a stick
         -Move a label: hold the label with the left-mouse-button
         -Remove one label: on the label, right-mouse-click
         -Export to xmgrace using the 'File->Export to xmagrace' option
        """
        QMessageBox.about(self, "About the app", msg.strip())
        
    #==========================================================
    # ANALYSIS FUNCTIONS
    #==========================================================
    def compute_moments(self):
        """
        Compute First and Second moments for the convoluted spectrum
        """
        x = self.spectrum_sim[0].get_xdata()
        y = self.spectrum_sim[0].get_ydata()
        
        # Zero
        m0 = np.trapz(y, x)
        y /= m0
        # First
        y = y*x
        m1 = np.trapz(y, x)
        # Second
        y = y*x
        m2 = np.trapz(y, x)
        # Sigma
        sgm = np.sqrt(m2-m1**1)
        
        result = """  MOMENTA ANALYSIS
  ====================
  
  * Covoluted Spectrum
  ---------------------------------
  1st Moment (eV) = %.3f
  
  2nd Moment (eV^2) = %.3f
  
  Sigma (eV) = %.3f
  ---------------------------------
        """ % (m1, m2, sgm)
        
        if self.spectrum_exp != None:
            x = self.spectrum_exp[0].get_xdata()
            y = self.spectrum_exp[0].get_ydata()
            
            # Zero
            m0 = np.trapz(y, x)
            y /= m0
            # First
            y = y*x
            m1 = np.trapz(y, x)
            # Second
            y = y*x
            m2 = np.trapz(y, x)
            # Sigma
            sgm = np.sqrt(m2-m1**1)
            # Add to message
            result = result+"""

  * Loaded Spectrum
  ---------------------------------
  1st Moment (eV) = %.3f
  
  2nd Moment (eV^2) = %.3f
  
  Sigma (eV) = %.3f
  ---------------------------------
        """ % (m1, m2, sgm)
        
        self.analysis_box.setText(result)
        
        
    #==========================================================
    # LOAD DATA AND ELEMENTS
    #==========================================================
    def load_sticks(self):
        """ 
        Load stick spectra for all classes (C0,C1...,CHot)
        - The spectra objects are stored in a list: self.stickspc
        """
        # clear the axes and redraw the plot anew
        # 
        self.axes.set_title('TI stick spectrum from $\mathcal{FC}classes$',fontsize=18)
        self.axes.set_xlabel('Energy (eV)',fontsize=16)
        self.axes.set_ylabel('Stick Intensity',fontsize=16)
        self.axes.tick_params(direction='out',top=False, right=False)
        
        
        #Plotting sticks and store objects
        # Set labels and colors
        label_list = ['0-0']+[ 'C'+str(i) for i in range(1,8) ]+['Hot']
        color_list = ['k', 'b', 'r', 'g', 'c', 'm', 'brown', 'pink', 'orange' ]


        #Inialize variables
        self.stickspc = []
        xmin =  999.
        xmax = -999
        for iclass in range(9):
            x = np.array([ self.fcclass_list[iclass][i].DE        for i in range(len(self.fcclass_list[iclass])) ])
            y = np.array([ self.fcclass_list[iclass][i].intensity for i in range(len(self.fcclass_list[iclass])) ])
            z = np.zeros(len(x))
            if len(x) == 0:
                self.stickspc.append(None)
            else:
                self.stickspc.append(self.axes.vlines(x,z,y,linewidths=1,color=color_list[iclass],
                                                      label=label_list[iclass],picker=5))
                f = open('class'+str(iclass)+'.dat','w')
                f.write(str(x))
                f.close
                xmin = min([xmin,min(x)])
                xmax = max([xmax,max(x)])
                
        self.axes2.set_xlim([xmin-0.15,xmax+0.15])
        
        self.canvas.draw()
        
        
    def load_sticks_legend(self):
        """
        Plot legend, which is pickable so as to turn plots on/off
        """
        
        #Legends management
        self.legend = self.axes.legend(loc='upper right', fancybox=True, shadow=True)
        self.legend.get_frame().set_alpha(0.4)
        self.legend.set_picker(5)
        # we will set up a dict mapping legend line to orig line, and enable
        # picking on the legend line (from legend_picking.py)
        self.legend_lines = dict()
        # Note: mechanism to get rid out of None elements in the list
        #  filter(lambda x:x,lista)) evaluates every member in the list, and only take if
        #  the result of the evaluation is True. None gives a False
        for legline, origline in zip(self.legend.get_lines(), list(filter(lambda x:x,self.stickspc))):
            legline.set_picker(5)  # 5 pts tolerance
            self.legend_lines[legline] = origline
            
            
    def load_convoluted(self):
        str = unicode(self.textbox.text())
        hwhm = float(str)
        fixaxes = self.fixaxes_cb.isChecked()
        
        if self.data_type == "Lineshape":
            self.axes2.set_ylabel(r'Lineshape (a.u.)',fontsize=16)
        elif self.spc_type == 'abs':
            self.axes2.set_ylabel(r'$\varepsilon$ (dm$^3$mol$^{-1}$cm$^{-1}$)',fontsize=16)
        elif self.spc_type == 'ecd':
            self.axes2.set_ylabel(r'$\Delta\varepsilon$ (dm$^3$mol$^{-1}$cm$^{-1}$)',fontsize=16)
        else:
            self.axes2.set_ylabel('I',fontsize=16)
        self.axes2.set_xlabel('Energy (eV)',fontsize=16)
        #self.axes.tick_params(direction='out',top=False, right=False)
        
        #Convolution (in energy(eV))
        xc,yc = convolute([self.xbin,self.ybin],hwhm=hwhm,broad=self.broadening,input_bins=self.inputBins_cb.isChecked())
        if self.spc_type == 'abs':
            factor = 703.300
        elif self.spc_type == 'ecd':
            factor = 20.5288
        else:
            factor = 1.
        yc = yc * factor
        # Plot convoluted
        if self.spectrum_sim:
            self.spectrum_sim[0].remove()
        self.spectrum_sim = self.axes2.plot(xc,yc,'--',color='k')
        if not fixaxes:
            self.rescale_yaxis()
        
        self.canvas.draw()
        
        
    def update_convolute(self):
        str = unicode(self.textbox.text())
        hwhm = float(str)
        fixaxes = self.fixaxes_cb.isChecked()
        
        #Convolution (in energy(eV))
        xc,yc = convolute([self.xbin,self.ybin],hwhm=hwhm,broad=self.broadening,input_bins=self.inputBins_cb.isChecked())
        if self.spc_type == 'abs':
            factor = 703.300
        elif self.spc_type == 'emi':
            factor = 20.5288
        else:
            factor = 1.
        yc = yc * factor
        # Plot convoluted
        self.spectrum_sim[0].remove()
        self.spectrum_sim = self.axes2.plot(xc,yc,'--',color='k')
        if not fixaxes:
            self.rescale_yaxis()

        self.canvas.draw()
        
        
    def load_experiment_spc(self,x,y):
        fixaxes = self.fixaxes_cb.isChecked()
        
        x,y = [np.array(x), np.array(y)]
        # Plot experiment (only one experiment is allowed)
        if self.spectrum_exp != None:
            self.spectrum_exp[0].remove()
        self.spectrum_exp = self.axes2.plot(x,y,'-',color='gray')
        if not fixaxes:
            self.rescale_yaxis()
        
        self.canvas.draw()
        
    def rescale_yaxis(self):
        """"
        Set the range so as to keep the same zero as in the case of the sticks
        getting the maximum between exp and sim
        """
        ysim = self.spectrum_sim[0].get_ydata()
        if self.spectrum_exp != None:
            yexp = self.spectrum_exp[0].get_ydata()
            ymax2 = max(ysim.max(),yexp.max())
            ymin2 = min(ysim.min(),yexp.min())
        else:
            ymax2 = ysim.max()
            ymin2 = ysim.min()
            
        ymin,ymax = self.axes.get_ylim()
        if abs(ymin2) > abs(ymax2):
            ymin2 *= 1.05
            ymax2 = ymin2/ymin * ymax
        else:
            ymax2 *= 1.05
            ymin2 = ymax2/ymax * ymin
            
        self.axes2.set_ylim([ymin2,ymax2])
        
        return
        
        
    #==========================================================
    # FUNCTIONS TO INTERACT WITH THE PLOT
    #==========================================================
    def on_pick(self, event):
        """"
        This is a common manager for picked objects
        
        The event received here is of the type
        matplotlib.backend_bases.PickEvent, they
        differeciate the artist
        
        "Pickable" opjects are labels and sticks
        but they have different attributes and, thus,
        need to be handled differently
        """
        if type(event.artist) == matplotlib.collections.LineCollection:
            self.select_stick(event)
        elif type(event.artist) == matplotlib.text.Annotation:
            self.active_label = event.artist
        elif type(event.artist) == matplotlib.lines.Line2D:
            self.del_stick_marker()
            self.interact_with_legend(event)
            
            
    def select_stick(self,event):
        """
        Select a given stick transiton by clicking with the mouse, and do:
         1) Put a label if the left-button is clicked
         2) Highlight is right button is clicked
        """
        x = event.mouseevent.xdata
        y = event.mouseevent.ydata

        iclass = self.stickspc.index(event.artist)

        #Now set data and label positions
        stick_x = [ self.fcclass_list[iclass][i].DE        for i in event.ind ]
        stick_y = [ self.fcclass_list[iclass][i].intensity for i in event.ind ]
        distances = np.hypot(x-stick_x, y-stick_y)
        indmin = distances.argmin()
        dataind = event.ind[indmin]
        
        # Highlight or add label
        tr = self.fcclass_list[iclass][dataind]
        if event.mouseevent.button == 3:
            self.active_tr = tr
            self.set_stick_marker()
        elif event.mouseevent.button == 1:
            # The transition info need to be gathered
            self.fcclass_list[iclass][dataind].info()
            self.add_Label(tr)


    def on_press_key(self, event):
        """"
        Manage keyword interactions with the graph
        """
        if self.active_tr is None: 
            return
        if event.key not in ('+', '-'): 
            return
        if event.key=='+': 
            inc = 1
        else:  
            inc = -1

        # Get the active class
        if self.active_tr.motherstate == 1:
            iclass = self.active_tr.fcclass
        else:
            iclass = 8 #Hot bands class
        index = self.fcclass_list[iclass].index(self.active_tr)
        index += inc
        
        # Manage transition between classes
        if index > len(self.fcclass_list[iclass])-1:
            iclass += 1
            index = 0
        elif index < 0:
            iclass -= 1
            try:
                index = len(self.fcclass_list[iclass])-1
            except:
                pass
        
        if iclass > 8 or iclass < 0:
            self.del_stick_marker()
        else:
            self.active_tr = self.fcclass_list[iclass][index]
            self.set_stick_marker()
        
        
    def on_press_mouse(self,event):
        self.past_event = None
        if self.active_label is None:
            return
        self.past_event = event
        
        
    def move_label(self,event):
        if self.active_label is None: return
        if event.button != 1: return
        if self.past_event is  None or event.inaxes!=self.past_event.inaxes: return
    
        # The label is picked even if the connecting line
        # is pressed. Since, this is not a nice behabiour 
        # we reject the press events done on the line
        x0, y0 = self.active_label.get_position()
        xe, ye = self.past_event.xdata,self.past_event.ydata
        x_range=self.axes.get_xlim()
        # Set the presision based on the plot scale
        eps_x = (x_range[1]-x_range[0])/50.
        y_range=self.axes.get_ylim()
        eps_y = (y_range[1]-y_range[0])/50.
        if abs(x0-xe) > eps_x and abs(x0-xe) > eps_y:
            return
        # Get the plot distance
        
        dx = event.xdata - self.past_event.xdata
        dy = event.ydata - self.past_event.ydata
        self.active_label.set_position((x0+dx,y0+dy))
        self.canvas.draw()
        # Update the pressevent
        self.past_event = event
        
        
    def release_label(self,event):
        if self.active_label is None: return
        if event.button != 1: return
        if event.inaxes!=self.axes:
         return
        self.past_event = None
        self.active_label = None
        
        
    def delete_label(self,event):
        if self.active_label is None: return
        if event.button != 3: return
    
        # As in the move_label, only remove if we click
        # on the text (not on the line)
        x0, y0 = self.active_label.get_position()
        xe, ye = self.past_event.xdata,self.past_event.ydata
        x_range=self.axes.get_xlim()
        # Set the presision based on the plot scale
        eps_x = (x_range[1]-x_range[0])/70.
        y_range=self.axes.get_ylim()
        eps_y = (y_range[1]-y_range[0])/70.
        if abs(x0-xe) > eps_x and abs(x0-xe) > eps_y:
            return
    
        #Remove the label
        self.active_label.remove()
        #And substract the corresponding entry from the dict
        self.labs.pop(self.active_label)
        #We deactivate the lab. Otherwise, if we reclikc on the same point, it raises an error
        self.active_label.set_visible(False)
        self.canvas.draw()


    def interact_with_legend(self,event):
        """
        DESCRIPTION
        ------------
        Function to activate/deactivate a plot, clicking on the legend 
        
        NOTES
        -----
        Based on matplotlib example: legend_picking.py
        http://matplotlib.org/examples/event_handling/legend_picking.html
        """
        # on the pick event, find the orig line corresponding to the
        # legend proxy line, and toggle the visibility
        legline = event.artist
        class_spc = self.legend_lines[legline]
        vis = not class_spc.get_visible()
        class_spc.set_visible(vis)
        # Change the alpha on the line in the legend so we can see what lines
        # have been toggled
        if vis:
            legline.set_alpha(1.0)
        else:
            legline.set_alpha(0.2)
            
        self.canvas.draw()
            
    # FUNCTIONS WITHOUT EVENT
    def set_stick_marker(self):
        if self.active_tr is None: return
        
        tr = self.active_tr 
        stick_x = tr.DE
        stick_y = tr.intensity
        
        # Add transition info to analysis_box
        self.analysis_box.setText(self.active_tr.info())
        
        self.selected.set_visible(False)
        self.selected  = self.axes.vlines([stick_x], [0.0], [stick_y], linewidths=3,
                                  color='yellow', visible=True, alpha=0.7)
        self.canvas.draw()
        
    
    def del_stick_marker(self):
        
        self.analysis_box.setText("")
        self.active_tr = None 
        self.selected.set_visible(False)
        self.canvas.draw()
        
    def reset_labels(self):
        #We need a local copy of labs to iterate while popping
        labs_local = [ lab for lab in self.labs ]
        for lab in labs_local:
            lab.remove()
            self.labs.pop(lab)
        self.canvas.draw()
        
        
    def add_Label(self,tr):
        
        stick_x = tr.DE
        stick_y = tr.intensity
        
        xd = stick_x
        yd = stick_y
        xl = stick_x - 0.00
        #Since the intensity may change several orders of magnitude, 
        # we better don't shift it
        yl = stick_y + 0.0
        
        #Define label as final modes description
        if tr.fcclass == 0 and tr.motherstate == 1:
            label='0-0'
            agrlabel='0-0'
        else:
            label='$'
            agrlabel=''
            if tr.motherstate > 1:
                # For Hot bands, write also initial state
                for i in range(0,len(tr.init)):
                    label = label+str(tr.init[i])+'^{'+str(tr.qinit[i])+'},'
                    agrlabel = agrlabel+str(tr.init[i])+'\S'+str(tr.qinit[i])+'\N,'
                if len(tr.init) == 0:
                    label=label+"0,"
                    agrlabel=agrlabel+"0,"
                label = label[0:-1]+'-'
                agrlabel = agrlabel[0:-1]+'-'
            for i in range(0,len(tr.final)):
                label = label+str(tr.final[i])+'^{'+str(tr.qfinal[i])+'},'
                agrlabel = agrlabel+str(tr.final[i])+'\S'+str(tr.qfinal[i])+'\N,'
            if len(tr.final) == 0:
                label=label+"0,"
                agrlabel=agrlabel+"0,"
            #Remove trailing comma
            label = label[0:-1]+'$'
            agrlabel = agrlabel[0:-1]

        #In labelref we get the annotation class corresponding to the 
        #current label. labelref is Class(annotation)
        labelref = self.axes.annotate(label, xy=(xd, yd), xytext=(xl, yl),picker=1,
                            arrowprops=dict(arrowstyle="-",
                                            color='grey'))

        #Check whether the label was already assigned or not
        set_lab = True
        for labref in self.labs:
            lab = self.labs[labref]
            if lab == agrlabel:
                print "This label was already defined"
                set_lab = False
        if set_lab:
            # The dictionary labs relates each labelref(annotation) to 
            # the agrlabel. Note that the mpl label can be retrieved
            # from labelref.get_name()
            self.labs[labelref] = agrlabel
            self.canvas.draw()
        else:
            labelref.remove()
           
        
    def update_hwhm_from_slider(self,UpdateConvolute=True):
        hwhmmin = 0.01
        hwhmmax = 0.1
        slidermin = 1   # this is not changed
        slidermax = 100 # this is not changed
        hwhm = float((hwhmmax-hwhmmin)/(slidermax-slidermin) * (self.slider.value()-slidermin) + hwhmmin)
        hwhm = round(hwhm,3)
        self.textbox.setText(str(hwhm))
        if (UpdateConvolute):
            self.update_convolute()
        
        
    def update_hwhm_from_textbox(self):
        hwhmmin = 0.01
        hwhmmax = 0.1
        slidermin = 1   # this is not changed
        slidermax = 100 # this is not changed
        str = unicode(self.textbox.text())
        hwhm = float(str)
        sliderval = int((slidermax-slidermin)/(hwhmmax-hwhmmin) * (hwhm-hwhmmin) + slidermin)
        sliderval = min(sliderval,slidermax)
        sliderval = max(sliderval,slidermin)
        self.slider.setValue(sliderval)
        self.update_convolute()
        
        
    def update_broad_function(self):
        self.broadening = self.select_broad.currentText()
        self.update_convolute()
        
        
    def update_data_type(self):
        current_data_type = self.data_type
        self.data_type = self.select_data_type.currentText()
        
        if current_data_type != self.data_type:
            exp = {"abs":1,"ecd":1,"emi":3,"cpl":3}
            n = exp[self.spc_type]
            if self.data_type == "Lineshape":
                self.ybin /= (self.xbin / 27.2116)**n * 703.30
            elif self.data_type == "Intensity":
                self.ybin *= (self.xbin / 27.2116)**n * 703.30
            self.load_convoluted()
      
        
    #==========================================================
    # MAIN FRAME, CONNECTIONS AND MENU ACTIONS
    #==========================================================    
    def create_main_frame(self):
        self.main_frame = QWidget()
        
        # Create the mpl Figure and FigCanvas objects. 
        # 5x4 inches, 100 dots-per-inch
        #
        #self.dpi = 100
        #self.fig = Figure((5.0, 4.0), dpi=self.dpi)
        # (lo de arriba, estaba en el original)
        # 
        # Usamos la figura/ejes creados com subplots
        self.fig, self.axes2 = plt.subplots()
        # Second axis for the convoluted graph
        self.axes = self.axes2.twinx()
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setParent(self.main_frame)
        #self.canvas.setMaximumWidth(1000)
        # The following allows the interaction with the keyboard
        self.canvas.setFocusPolicy( Qt.ClickFocus )
        self.canvas.setFocus()
        
        # Since we have only one plot, we can use add_axes 
        # instead of add_subplot, but then the subplot
        # configuration tool in the navigation toolbar wouldn't
        # work.
        #
        #self.axes = self.fig.add_subplot(111)
        
        # Bind events to interact with the graph
        # Picking maganement
        self.canvas.mpl_connect('pick_event', self.on_pick)
        #Manage labels
        self.canvas.mpl_connect('button_press_event', self.on_press_mouse)
        self.canvas.mpl_connect('button_release_event', self.release_label)
        self.canvas.mpl_connect('motion_notify_event', self.move_label)
        self.canvas.mpl_connect('button_press_event', self.delete_label)
        # Manage highlighting
        self.canvas.mpl_connect('key_press_event', self.on_press_key)
        
        # Create the navigation toolbar, tied to the canvas
        #
        self.mpl_toolbar = NavigationToolbar(self.canvas, self.main_frame)
        
        # Other GUI controls
        # 
        self.textbox = QLineEdit()
        self.textbox.setMinimumWidth(50)
        self.textbox.setMaximumWidth(50)
        self.connect(self.textbox, SIGNAL('editingFinished ()'), self.update_hwhm_from_textbox)
        
        self.clean_button1 = QPushButton("&Clean(Panel)")
        self.connect(self.clean_button1, SIGNAL('clicked()'), self.del_stick_marker)
        self.clean_button2 = QPushButton("&Clean(Labels)")
        self.connect(self.clean_button2, SIGNAL('clicked()'), self.reset_labels)
        
        self.select_broad = QComboBox()
        self.select_broad.addItems(["Gau","Lor"])
        self.select_broad.currentIndexChanged.connect(self.update_broad_function)
        
        self.select_data_type = QComboBox()
        self.select_data_type.addItems(["Intensity","Lineshape"])
        self.select_data_type.currentIndexChanged.connect(self.update_data_type)
        
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMaximumWidth(200)
        self.slider.setRange(1, 100)
        self.slider.setValue(30)
        self.slider.setTracking(True)
        self.slider.setTickPosition(QSlider.TicksBothSides)
        self.connect(self.slider, SIGNAL('valueChanged(int)'), self.update_hwhm_from_slider)
        
        self.fixaxes_cb = QCheckBox("Fix y-axis")
        self.fixaxes_cb.setChecked(False)
        self.fixaxes_cb.setMaximumWidth(100)
        
        self.inputBins_cb = QCheckBox("Input bins")
        self.inputBins_cb.setChecked(False)
        self.inputBins_cb.setMaximumWidth(100)
        
        # Labels
        hwhm_label  = QLabel('   HWHM')
        eV_label    = QLabel('(eV)')
        broad_label = QLabel('Broadening')
        datatype_label = QLabel('Data Type')
        # Splitters
        vline = QFrame()
        vline.setFrameStyle(QFrame.VLine)
        vline.setLineWidth(1)
        vline2 = QFrame()
        vline2.setFrameStyle(QFrame.VLine)
        vline2.setLineWidth(1)
        
        # Analysis box
        self.analysis_box = QTextEdit(self.main_frame)
        self.analysis_box.setReadOnly(True)
        self.analysis_box.setMinimumWidth(150)
        self.analysis_box.setMaximumWidth(200)
        
        #
        # Layout with box sizers
        # 
        # Broad selector
        vbox_select = QVBoxLayout()
        vbox_select.addWidget(broad_label)
        vbox_select.addWidget(self.select_broad)
        # HWHM slider with textbox
        hbox_slider = QHBoxLayout()
        hbox_slider.addWidget(self.slider)
        hbox_slider.addWidget(self.textbox)
        hbox_slider.addWidget(eV_label)
        # HWHM label with inputBins checkbox
        hbox_hwhmlab = QHBoxLayout()
        hbox_hwhmlab.addWidget(hwhm_label)
        hbox_hwhmlab.setAlignment(hwhm_label, Qt.AlignLeft)
        hbox_hwhmlab.addWidget(self.inputBins_cb)
        hbox_hwhmlab.setAlignment(self.inputBins_cb, Qt.AlignLeft)
        # Complete HWHM widget merging all box here
        vbox_slider = QVBoxLayout()
        vbox_slider.addLayout(hbox_hwhmlab)
        vbox_slider.setAlignment(hbox_hwhmlab, Qt.AlignLeft)
        vbox_slider.addLayout(hbox_slider)
        vbox_slider.setAlignment(hbox_slider, Qt.AlignLeft)
        # Clean button
        vbox_cleaner = QVBoxLayout()
        vbox_cleaner.addWidget(self.clean_button1)
        vbox_cleaner.addWidget(self.clean_button2)
        # DataType sector
        vbox_datatype = QVBoxLayout()
        vbox_datatype.addWidget(datatype_label)
        vbox_datatype.setAlignment(datatype_label, Qt.AlignLeft)
        vbox_datatype.addWidget(self.select_data_type)
        vbox_datatype.setAlignment(self.select_data_type, Qt.AlignLeft)
        ## MAIN LOWER BOX
        hbox = QHBoxLayout()
        hbox.addLayout(vbox_cleaner)
        hbox.addWidget(vline)
        hbox.addLayout(vbox_select)
        hbox.setAlignment(vbox_select, Qt.AlignTop)
        hbox.addLayout(vbox_slider)
        hbox.setAlignment(vbox_slider, Qt.AlignTop)
        hbox.addWidget(vline2)
        hbox.setAlignment(vline2, Qt.AlignLeft)
        hbox.addLayout(vbox_datatype)
        hbox.setAlignment(vbox_datatype, Qt.AlignTop)
        
        # Hbox below plot
        hbox2 = QHBoxLayout()
        hbox2.addWidget(self.fixaxes_cb)
        hbox2.setAlignment(self.fixaxes_cb, Qt.AlignLeft)
        hbox2.addWidget(self.mpl_toolbar)
        hbox2.setAlignment(self.mpl_toolbar, Qt.AlignLeft)
            
        #hbox_plot = QHBoxLayout()
        #hbox_plot.addWidget(self.canvas)
        #hbox_plot.addWidget(self.analysis_box)
        #hbox_plot.addStretch(1)
        
        #VMainBox = QVBoxLayout()
        #VMainBox.addLayout(hbox_plot)
        #VMainBox.addWidget(self.mpl_toolbar)
        #VMainBox.setAlignment(self.mpl_toolbar, Qt.AlignLeft)
        #VMainBox.addLayout(hbox)

        grid = QGridLayout()
        grid.setSpacing(10)
        
        #                   (row-i,col-i,row-expand,col-expand)     
        grid.addWidget(self.canvas,      0,0 ,1,15)
        grid.addWidget(self.analysis_box,0,15,1,1)
        grid.addLayout(hbox2,            1,0 ,1,15)
        grid.addLayout(hbox,             2,0 ,1,13)
        grid.setAlignment(hbox,   Qt.AlignLeft)
        grid.setAlignment(hbox2,  Qt.AlignLeft)
        
        self.main_frame.setLayout(grid)
        
        self.setCentralWidget(self.main_frame)
    
    def create_status_bar(self):
        self.status_text = QLabel("UV spectrum")
        self.statusBar().addWidget(self.status_text, 1)
        
    def create_menu(self):        
        # /File
        self.file_menu = self.menuBar().addMenu("&File")
        load_file_action = self.create_action("&Save plot",
            shortcut="Ctrl+S", slot=self.save_plot, 
            tip="Save the plot")
        quit_action = self.create_action("&Quit", slot=self.close, 
            shortcut="Ctrl+Q", tip="Close the application")
        xmgr_export_action = self.create_action("&Export to xmgrace", slot=self.xmgr_export, 
            shortcut="Ctrl+E", tip="Export to xmgrace format")
        spc_import_action = self.create_action("&Import plot", slot=self.open_plot, 
            shortcut="Ctrl+N", tip="Import spectrum")
        # Now place the actions in the menu
        self.add_actions(self.file_menu, 
            (load_file_action, xmgr_export_action, spc_import_action, None, quit_action))
        
        # /Analyze
        self.anlyze_menu = self.menuBar().addMenu("&Analyze")
        momenta_action = self.create_action("&Momenta", 
            slot=self.compute_moments, 
            tip='Compute moments')
        self.add_actions(self.anlyze_menu, (momenta_action,))
        
        # /Manipulate
        self.manip_menu = self.menuBar().addMenu("&Manipulate")
        
        self.help_menu = self.menuBar().addMenu("&Help")
        about_action = self.create_action("&About", 
            shortcut='F1', slot=self.on_about, 
            tip='About the demo')
        self.add_actions(self.help_menu, (about_action,))

    def add_actions(self, target, actions):
        for action in actions:
            if action is None:
                target.addSeparator()
            else:
                target.addAction(action)

    def create_action(  self, text, slot=None, shortcut=None, 
                        icon=None, tip=None, checkable=False, 
                        signal="triggered()"):
        action = QAction(text, self)
        if icon is not None:
            action.setIcon(QIcon(":/%s.png" % icon))
        if shortcut is not None:
            action.setShortcut(shortcut)
        if tip is not None:
            action.setToolTip(tip)
            action.setStatusTip(tip)
        if slot is not None:
            self.connect(action, SIGNAL(signal), slot)
        if checkable:
            action.setCheckable(True)
        return action
    
    
#==========================================================
# GLOBAL FUNCTIONS
#==========================================================
# FILE READERS
def read_fort21(MaxClass):
    """
    Function to extract transtion infor from fort.21 file
    The content is taken from the standard version and may
    need some polish
    
    Arguments:
     MaxClass (int): maximum class to be loaded (0 to 7)
                     Hot bands are always loaded
    """
    # Open and read file
    tr=[]
    print "Loading transitions (fort.21)..."
    try:
        f = open('fort.21','r')
    except:
        exit("ERROR: Cannot open file 'fort.21'")
        
    #First read 0-0 transition
    itrans = 0
    for line in f:
        if "INDEX" in line:
            line = f.next()
            data = line.split()
            tr.append(spectral_transition())
            tr[itrans].motherstate = 1
            tr[itrans].fcclass     = 0
            tr[itrans].index       = float(data[0])
            tr[itrans].einit       = float(data[1])
            tr[itrans].efin        = float(data[2])
            tr[itrans].DE          = float(data[3])
            tr[itrans].DE00cm      = float(data[4])
            tr[itrans].fcfactor    = float(data[5])
            """
            Sometimes, intens for 0-0 is ******
            Could be read from fort.8 although 
            the cleanest is to fix it fcclasses
            """ 
            try: tr[itrans].intensity   = float(data[6])
            except: exit("ERROR: Check 0-0 transition") 
            #For this case, modes are assigned manually
            tr[itrans].init = [0] 
            tr[itrans].final = [0] 
            #Now break to continue with other Classes
            break

    nhot = 0
    nclass1 = 0
    nclass2 = 0
    nclass3 = 0
    nclass4 = 0
    nclass5 = 0
    nclass6 = 0
    nclass7 = 0
    for line in f:
        if "MOTHER STATE" in line:
            motherstate = int(line.split("N.")[1])
        elif "C1 " in line:
            fcclass = 1
            if motherstate == 1:
                nclass = 0
        elif "C2 " in line:
            fcclass = 2
            if motherstate == 1:
                nclass1 = nclass
                nclass = 0
        elif "C3 " in line:
            fcclass = 3
            if motherstate == 1:
                nclass2 = nclass
                nclass = 0
        elif "C4 " in line:
            fcclass = 4
            if motherstate == 1:
                nclass3 = nclass
                nclass = 0
        elif "C5 " in line:
            fcclass = 5
            if motherstate == 1:
                nclass4 = nclass
                nclass = 0
        elif "C6 " in line:
            fcclass = 6
            if motherstate == 1:
                nclass5 = nclass
                nclass = 0
        elif "C7 " in line:
            fcclass = 7
            if motherstate == 1:
                nclass6 = nclass
                nclass = 0
        elif "M-0 TRANSITION" in line and motherstate == 2:
            if fcclass == 1:
                nclass1 = nclass
            elif fcclass == 2:
                nclass2 = nclass
            elif fcclass == 3:
                nclass3 = nclass
            elif fcclass == 4:
                nclass4 = nclass
            elif fcclass == 5:
                nclass5 = nclass
            elif fcclass == 6:
                nclass6 = nclass
            elif fcclass == 7:
                nclass7 = nclass
            nclass = 0
            fcclass = 0
        elif ("E+" in line) | ("E-" in line):
            nclass += 1
            if fcclass<=MaxClass:
                data = line.split()
                itrans += 1
                tr.append(spectral_transition())
                tr[itrans].motherstate = motherstate
                tr[itrans].fcclass     = fcclass
                tr[itrans].index       = float(data[0])
                tr[itrans].efin        = float(data[1])
                tr[itrans].einit       = float(data[2])
                tr[itrans].DE          = float(data[3])
                tr[itrans].DE00cm      = float(data[4])
                tr[itrans].fcfactor    = float(data[5])
                tr[itrans].intensity   = float(data[6])
        #Indentify modes in the transition
        #Initial
        elif 'state 1 = GROUND' in line and fcclass<=MaxClass:
            tr[itrans].init = [0]
        elif 'Osc1=' in line:
            A = line.split('Osc1=')
            del A[0]
            for i in range(0,len(A)):
                A[i] = int(A[i])
            tr[itrans].init = A 
        #Number of quanta involved
        elif 'Nqu1=' in line and fcclass<=MaxClass:
            A = line.split('Nqu1=')
            del A[0]
            for i in range(0,len(A)):
                A[i] = int(A[i])
            tr[itrans].qinit = A 
        #Final
        elif 'state 1 = GROUND' in line and fcclass<=MaxClass:
            tr[itrans].final = [0]
        elif 'Osc2=' in line and fcclass<=MaxClass:
            A = line.split('Osc2=')
            del A[0]
            for i in range(0,len(A)):
                A[i] = int(A[i])
            tr[itrans].final = A 
        #Number of quanta involved
        elif 'Nqu2=' in line and fcclass<=MaxClass:
            A = line.split('Nqu2=')
            del A[0]
            for i in range(0,len(A)):
                A[i] = int(A[i])
            tr[itrans].qfinal = A 
    #If there were mother states>1, no nclass7 was already updated, otherwise:
    if tr[itrans].motherstate == 1: nclass7 = nclass
    else: nhot = nclass

    f.close()
    
    # Load filter transitions if required
    loadC=True
    nclass_list = [nclass1,nclass2,nclass3,nclass4,nclass5,nclass6,nclass7]
    print 'Transitions read:'
    print ' Class     N. trans.         Load?  '
    for i,nclass in enumerate(nclass_list):
        if MaxClass<i+1: loadC=False
        print ' C{0}        {1:5d}             {2}   '.format(i+1,nclass,loadC)
        if MaxClass<i+1: nclass_list[i]=0
    print     ' Hot       {0:5d}                   '.format(nhot)
    nclass_list.append(nhot)
    print ''
    print 'Loaded transitions: ',(itrans)
    #========== Done with fort.21 ====================================

    # This is a conversion from old stile reader to class_list
    # maybe it'd be better to change the code above
    class_list = []
    for nclass in [1]+nclass_list:
        class_list.append([tr.pop(0) for i in range(nclass)])

    return class_list


def read_spc_xy(filename):
    """
    Function to read fort.22, whic contains the bins to reconstruct
    the convoluted spectrum_sim.
    This is a simple [x,y] file
    """
    # Open and read file
    print "Loading spectral data from '"+filename+"'..."
    try:
        f = open(filename,'r')
    except:
        exit("ERROR: Cannot open file '"+filename+"'")
    i = 0
    x = []
    y = []
    
    for line in f:
        data = line.split()
        try:
            x.append(float(data[0]))
            y.append(float(data[1]))
        except:
            continue

    f.close()

    return x,y

# CONVOLUTION
def convolute(spc_stick,npoints=1000,hwhm=0.1,broad="Gau",input_bins=False):
    """
    Make a Gaussian convolution of the stick spectrum
    The spectrum must be in energy(eV) vs Intens (LS?)
    
    Arguments:
    spc_stick  list of list  stick spectrum as [x,y]
               list of array
    npoints    int           number of points (for the final graph)
                             Can be a bit more if input_bins is False
    hwhm       float         half width at half maximum
    
    Retunrs a list of arrays [xconv,yconv]
    """
    x = spc_stick[0]
    y = spc_stick[1]
   
    # ------------------------------------------------------------------------
    # Convert discrete sticks into a continuous function with an histogram
    # ------------------------------------------------------------------------
    # (generally valid, but the exact x values might not be recovered)
    # Make the histogram for an additional 20% (if the baseline is not recovered, enlarge this)
    extra_factor = 0.2
    recovered_baseline=False
    sigma = hwhm / np.sqrt(2.*np.log(2.))
    while not recovered_baseline:
        if input_bins:
            # Backup npoints
            npts = npoints
            npoints = len(x)
            xhisto = x
            yhisto = y
            width = (x[1] - x[0])
        else:
            extra_x = (x[-1] - x[0])*extra_factor
            yhisto, bins =np.histogram(x,range=[x[0]-extra_x,x[-1]+extra_x],bins=npoints,weights=y)
            # Use bin centers as x points
            width = (bins[1] - bins[0])
            xhisto = bins[0:-1] + width/2
        
        # ----------------------------------------
        # Build Gaussian (centered around zero)
        # ----------------------------------------
        dxgau = width
        # The same range as xhisto should be used
        # this is bad. We can get the same using 
        # a narrower range and playing with sigma.. (TODO)
        if npoints%2 == 1:
            # Zero is included in range
            xgau_min = -dxgau*(npoints/2)
            xgau_max = +dxgau*(npoints/2)
        else:
            # Zero is not included
            xgau_min = -dxgau/2. - dxgau*((npoints/2)-1)
            xgau_max = +dxgau/2. + dxgau*((npoints/2)-1)
        xgau = np.linspace(xgau_min,xgau_max,npoints)
        if broad=="Gau":
            ygau = np.exp(-xgau**2/2./sigma**2)/sigma/np.sqrt(2.*np.pi)
        elif broad=="Lor":
            ygau = hwhm/(xgau**2+hwhm**2)/np.pi
        else:
            sys.exit("ERROR: Unknown broadening function: "+broad)
        
        # ------------
        # Convolute
        # ------------
        # with mode="same", we get the original xhisto range.
        # Since the first moment of the Gaussian is zero, 
        # xconv is exactly xhisto (no shifts)
        yconv = np.convolve(yhisto,ygau,mode="same")
        xconv = xhisto

        # Check baseline recovery (only with automatic bins
        if yconv[0] < yconv.max()/100.0 and yconv[-1] < yconv.max()/100.0:
            recovered_baseline=True
        if input_bins:
            recovered_baseline=True
            # If the input_bins are larger than npts, then reduce the grid to npts
            if (len(xconv) > npts):
                skip = len(xconv)/npts + 1
                x = xconv[0::skip]
                y = yconv[0::skip]
                xconv = x
                yconv = y

        extra_factor = extra_factor + 0.05

    return [xconv,yconv]
    
# GENERATE XMGR
def export_xmgrace(filename,ax,class_list,spc,labs):
    """
    DESCRIPTION
    ------------
    Function to convert the current data into a xmgrace plot, including
    labels currently on the screen
    
    Variables
    * filename string : path to the file to save the export
    * ax,         mpl.axes        : graphic info
    * class_list  list of vlines  : stick spectra (classes)
    * spc         Line2D          : convoluted spectrum
    * labs        dict            : labels in xmgr format (arg: labels as annotation Class)
    """

    f = open(filename,'w')
    
    print >> f, "# XMGRACE CREATED BY FCC_ANALYZER"
    print >> f, "# Only data and labels. Format will"
    print >> f, "# be added by your default xmgrace"
    print >> f, "# defaults (including colors, fonts...)"
    print >> f, "# Except the followins color scheme:"
    print >> f, '@map color 0  to (255, 255, 255), "white"'
    print >> f, '@map color 1  to (0, 0, 0), "black"'
    print >> f, '@map color 2  to (0, 0, 255), "blue"'
    print >> f, '@map color 3  to (255, 0, 0), "red"'
    print >> f, '@map color 4  to (0, 139, 0), "green4"'
    print >> f, '@map color 5  to (0, 255, 255), "cyan"'
    print >> f, '@map color 6  to (255, 0, 255), "magenta"'
    print >> f, '@map color 7  to (188, 143, 143), "brown"'
    print >> f, '@map color 8  to (100, 0, 100), "pink"'
    print >> f, '@map color 9  to (255, 165, 0), "orange"'
    print >> f, '@map color 10 to (255, 255, 0), "yellow"'
    print >> f, '@map color 11 to (220, 220, 220), "grey"'
    print >> f, '@map color 12 to (0, 255, 0), "green"'
    print >> f, '@map color 13 to (148, 0, 211), "violet"'
    print >> f, '@map color 14 to (114, 33, 188), "indigo"'
    print >> f, '@map color 15 to (103, 7, 72), "maroon"'
    print >> f, '@map color 16 to (64, 224, 208), "turquoise"'
    print >> f, '@map color 17 to (50, 50, 50), "gris2"'
    print >> f, '@map color 18 to (100, 100, 100), "gris3"'
    print >> f, '@map color 19 to (150, 150, 150), "gris4"'
    print >> f, '@map color 20 to (200, 200, 200), "gris5"'
    print >> f, '@map color 21 to (255, 150, 150), "red2"'
    print >> f, '@map color 22 to (150, 255, 150), "green2"'
    print >> f, '@map color 23 to (150, 150, 255), "blue2"'  
    # Without the @version, it makes auto-zoom (instead of taking world coords) 
    print >> f, "@version 50123"
    print >> f, "@page size 792, 612"
    print >> f, "@default symbol size 0.010000"
    print >> f, "@default char size 0.800000"
    for lab in labs:
        print >> f, "@with line"
        print >> f, "@    line on"
        print >> f, "@    line g0"
        print >> f, "@    line loctype world"
        print >> f, "@    line color 20"
        print >> f, "@    line ",lab.xy[0],",",lab.xy[1],",",lab.xyann[0],",",lab.xyann[1]
        print >> f, "@line def"
        print >> f, "@with string"
        print >> f, "@    string on"
        print >> f, "@    string g0"
        print >> f, "@    string loctype world"
        print >> f, "@    string ", lab.xyann[0],",",lab.xyann[1]
        print >> f, "@    string def \"",labs[lab],"\""
    print >> f, "@with g0"
    # Set a large view
    print >> f, "@    view 0.150000, 0.150000, 1.2, 0.92"
    #Get plotting range from mplt
    x=ax.get_xbound()
    y=ax.get_ybound()
    print >> f, "@    world ",x[0],",",y[0],",",x[1],",",y[1]
    #Get xlabel from mplt
    print >> f, "@    xaxis  label \""+ax.get_xlabel()+"\""
    #Get tick spacing from mplt
    x=ax.get_xticks()
    y=ax.get_yticks()
    print >> f, "@    xaxis  tick major", x[1]-x[0]
    print >> f, "@    yaxis  tick major", y[1]-y[0]
    #Legend
    print >> f, "@    legend loctype view"
    print >> f, "@    legend 0.95, 0.9"
    #Now include data
    label_list = ['0-0']+[ 'C'+str(i) for i in range(1,8) ]+['Hot']
    color_list = [ 1, 2, 3, 4, 5, 6, 7, 8, 9]
    k=-1
    ymax = -999.
    ymin =  999.
    for iclass in range(9):
        if (len(class_list[iclass]) == 0):
            continue
        k += 1
        x = np.array([ class_list[iclass][i].DE        for i in range(len(class_list[iclass])) ])
        y = np.array([ class_list[iclass][i].intensity for i in range(len(class_list[iclass])) ])
        print >> f, "& %s"%(label_list[iclass])
        print >> f, "@type bar"
        print >> f, "@    s"+str(k)," line type 0"
        print >> f, "@    s"+str(k)," legend  \"%s\""%(label_list[iclass])
        print >> f, "@    s"+str(k)," symbol color %s"%(color_list[iclass])
        for i in range(len(x)):
            print >> f, x[i], y[i]
        ymax = max(ymax,y.max())
        ymin = max(ymin,y.min())
            
    # Convoluted spectrum. scaled TODO: use the alternative axis
    # This can be done either with another Graph or using alt-x axis
    k += 1
    x = spc.get_xdata()
    y = spc.get_ydata()
    if abs(ymax) > abs(ymin):
        scale_factor = ymax/y.max()
    else:
        scale_factor = abs(ymax)/abs(y.max())
    y *= scale_factor
    print >> f, "& Spect"
    print >> f, "@type xy"
    print >> f, "@    s"+str(k)," line type 1"
    print >> f, "@    s"+str(k)," line linestyle 3"
    print >> f, "@    s"+str(k)," line color %s"%(1)
    print >> f, "@    s"+str(k)," legend  \"Spec\""
    for i in range(len(x)):
        print >> f, x[i], y[i]
            
    f.close()


# INPUT PARSER
def get_args():
    
    # Default default options 
    final_arguments = dict()
    final_arguments["-maxC"]="7"
    final_arguments["-type"]="abs"
    final_arguments["-h"]=False
    
    # Get list of input args
    input_args_list = []
    iarg = -1
    for s in sys.argv[1:]:
        # get -flag [val] arguments 
        if s[0]=="-":
            iarg=iarg+1
            input_args_list.append([s])
        else:
            input_args_list[iarg].append(s)
            
    # Transform into dict. Associtaing lonely flats to boolean   
    input_args_dict=dict()
    for input_arg in input_args_list:
        if len(input_arg) == 1:
            # Boolean option. Can be -Bool or -noBool
            input_arg.append(True)
            if input_arg[0][1:3] == "no":
                input_arg[0] = "-" + input_arg[0][3:]
                input_arg[1] = not input_arg[1]
        elif len(input_arg) != 2:
            raise BaseException("Sintax error. Too many arguments")

        input_args_dict[input_arg[0]] = input_arg[1]
    
    for key,value in input_args_dict.iteritems():
        # Check it is allowed
        isValid = final_arguments.get(key,None)
        if isValid is None:
            raise BaseException("Sintax error. Unknown label: " + key)
        # If valid, update final argument
        final_arguments[key]=value
        
    if final_arguments.get("-h"):
        
        print """
 ----------------------------------------
           FCclasses analyzer
   A GUI to analyze FCclasses output 
 ----------------------------------------
        """
        print "Options"
        for key,value in final_arguments.iteritems():
            print "  ", key, value
        sys.exit()
        
    return final_arguments
        
    
    
def main():
    app = QApplication(sys.argv)
    form = AppForm()
    form.show()
    app.exec_()


if __name__ == "__main__":
    main()


