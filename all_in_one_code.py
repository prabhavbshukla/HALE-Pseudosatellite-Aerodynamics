# -*- coding: utf-8 -*-
"""
Created on Wed Jul  6 16:13:20 2022

@author: prabh
"""
# Definition of Functions
import shutil
import os
from bs4 import BeautifulSoup
import re
try:
    import urllib.request as urllib2
except ImportError:
    import urllib2

# Function to search for airfoils on UIUC database according to Keywords
def keyword_filter(keywords):
    # Open the webpage and create the soup
    html_page = urllib2.urlopen("https://m-selig.ae.illinois.edu/ads/coord_database.html")
    soup = BeautifulSoup(html_page , 'lxml')
    
    soup_string = soup.get_text().lower()
    soup_text = soup_string.split('\n')
    soup_list = soup_text
    
    filtered_airfoils = []
    
    for search_word in keywords: 
        for sentences in soup_list:
            if search_word in sentences:
                airfoil_dat = sentences.split(' \\')
                filtered_airfoils.append(airfoil_dat[0])

    return filtered_airfoils


# Function to write name and percentage thickness of the airfoil into a file
def print_airfoil(f, airfoil, thickness):    
    f.write(airfoil)
    f.write("\t")
    f.write(thickness)
    f.write("%")
    f.write("\n")


# Function to extract thickness data, record it and durther filter airfoils
def thickness_filter(limits, filtered_airfoils):
    thickness_dict = {}
    # Base file path on the Airfoil Tools Website
    baseFlpath = "http://airfoiltools.com"
    
    # File operations to write data into files
    f = open("checked_thickness_airfoils.txt", "w") # Used as a check to verify if all the airfoils have been iterated through
    g = open("certified_thickness_airfoils.txt", "w") # Used to keep track of shortlisted airfoils (based on thickness)

    exceptions = ['s8023.dat'] # Doesn't exist on airfoiltools.com
    
    for airfoil in filtered_airfoils:
        if airfoil not in exceptions:
            # General format of the link where information of each airfoil is available.
            link = baseFlpath + "/airfoil/details?airfoil=" + airfoil.split(".dat")[0] + "-il"
            
            # The page is opened in HTML format and Soup is created.
            html_page = urllib2.urlopen(link)
            soup = BeautifulSoup(html_page , 'lxml')
            
            # Conversion to string format
            soup = str(soup)
            # To split the string exactly where thickness is available
            # For eg. "..... Max thickness 8% ......" = [..... Max thickness, 8%......]
            soup = soup.split("Max thickness ")
            
            # Thickness is the first number in the second element of the array
            thickness = soup[1]
            # Isolating just the number for further usage
            thickness = thickness.split("%")
            thickness = thickness[0]
            # Updating in check airfoil
            print_airfoil(f, airfoil, thickness)
            
            # Writing the shortlisted airfoil after verifying thickness limits
            if(float(thickness) < limits[1] and float(thickness) > limits[0]):
                print_airfoil(g, airfoil, thickness)
                thickness_dict[airfoil] = thickness
    
    f.close()
    g.close()
    return thickness_dict


# Now that airfoils are filtered and data stored in text files
# Function to download required airfoils using the text files
def download_airfoils(filename):
    f = open(filename, 'r')
    lines = f.readlines() # Read line by line, certified thickness file
    airfoil_dwnld = [] # List to store thickness certified airfoil names
	
    # Creating a list of all the certified airfoils
    for line in lines:
        airfoil_dwnld.append(line.split("\t")[0])	
    
    # Base file path on the UIUC Website
    baseFlpath = "https://m-selig.ae.illinois.edu/ads/"
    
    # Open the webpage and create the soup
    html_page = urllib2.urlopen("https://m-selig.ae.illinois.edu/ads/coord_database.html")
    soup = BeautifulSoup(html_page , 'lxml')
    
    precceding_extension = ['coord/', 'coord_updates/']

    # Loop over all the relevant files and save each one
    links = []
    for extensions in precceding_extension:
        for airfoils in airfoil_dwnld:
            for link in soup.find_all('a', attrs={'href': re.compile(extensions+airfoils)}):
                links.append(link.get('href'))
                
                urllib2.urlretrieve(baseFlpath+link.get('href'), link.get('href').rsplit('/', 1)[-1])
    return airfoil_dwnld

# Function to move airfoils to a directory
def move_files(airfoils):
    # Exception handling in case the directory already exists
    try:
        os.mkdir("Airfoils")
    finally:
        for airfoil in airfoils:
            source = airfoil
            destination = "Airfoils/" + airfoil
            shutil.move(source, destination)

#%% Calling the functions

search = ['low reynolds', 'laminar flow'] # Keywords to search UIUC Database
limits = [11, 13] # Thickness lower and upper limits

# Uncomment next two lines on first ever run
# airfoils_filter = keyword_filter(search)
# airfoils_thickness = thickness_filter(limits, airfoils_filter)

# Downloading airfoils
thickness_txt = "certified_thickness_airfoils.txt"
downloaded_airfoils = download_airfoils(thickness_txt)
move_files(downloaded_airfoils)

#%% Characteristic Filter
# This part of the code should be run after obtaining polars from XFLR
# The polars must be

from os import listdir, mkdir
from os.path import isfile, join
import numpy as np

# Function to filter airfoils based on aerodynamic data of the airfoil
# Returns a dictionary of airfoils and the criteria met
def characteristic_filter(min_lift, min_aoa, filtered_airfoils, mypath):
    # Dictionary to store the airfoils which meet the first criteria of lift
    lift_criteria = {}
    for airfoil in filtered_airfoils:
        data = np.genfromtxt(mypath + airfoil, skip_header= 10, delimiter = ",")
        alpha = data[:,0]
        cl = data[:,1]
        flag = 1
        # Loop to find the first occurrence of CL above 1.33
        for index in range(len(alpha)):
            if(cl[index] >= min_lift and flag == 1):
                if(alpha[index] < min_aoa):
                    lift_criteria[airfoil] = alpha[index]
                    flag = 0
    return lift_criteria

# Function to write the aerodynamic characteristics into a text file
def write_char_filter(lift_criteria, mypath):
    try:
        mkdir("Final_Airfoils")
    finally:
        # Write Required Data into a file
        for airfoil in lift_criteria.keys():
            data = np.genfromtxt(mypath + airfoil, skip_header= 10, delimiter = ",")
            # Variable to store the index of the first angle of attack that is positive
            zero_pos = list(data[:,0]).index(list(filter(lambda i: i > 0, data[:,0]))[0])
            alpha = data[zero_pos:,0]
            cl = data[zero_pos:,1]
            cd = data[zero_pos:,2]
            endurance = []
            for index in range(len(alpha)):
                endurance.append(cl[index]**(3/2)/cd[index])
                
            to_write = np.column_stack((alpha, cl, cd, endurance))
            np.savetxt("Final_Airfoils/" + airfoil, to_write, delimiter=",", header = "AoA, Cl, Cd, Endurance")

# Get all the airfoil file names
mypath = "Polars/"
filtered_airfoils = [f for f in listdir(mypath) if isfile(join(mypath, f))]

req_lift = 1.33 # Minimum lift required
max_aoa = 5 # Maximum AoA at which minimum lift is achieved

lift_pass = characteristic_filter(req_lift, max_aoa, filtered_airfoils, mypath)
write_char_filter(lift_pass, mypath)
