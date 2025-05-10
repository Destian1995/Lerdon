# all libraries
import os
import shutil
import random
import ast
import logging
import sqlite3
import json
import time
import threading

# kivy libraries
from kivy.animation import Animation
from kivy.app import App
from kivy.graphics import Line, Color, Rectangle, RoundedRectangle
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.widget import Widget
from kivy.core.text import Label as CoreLabel
from kivy.uix.carousel import Carousel
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.image import Image
from kivy.metrics import dp, sp
from kivy.utils import get_color_from_hex, platform
from kivy.clock import Clock
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.slider import Slider
from kivy.uix.dropdown import DropDown
from kivy.uix.modalview import ModalView
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.progressbar import ProgressBar
from kivy.uix.spinner import Spinner
from kivy.properties import partial, StringProperty, NumericProperty, ObjectProperty, ListProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.core.window import Window
from kivy.uix.screenmanager import Screen