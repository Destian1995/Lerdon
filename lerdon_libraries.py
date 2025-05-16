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
from kivy.graphics import Line, Color, Rectangle, RoundedRectangle, InstructionGroup
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.widget import Widget
from kivy.core.text import Label as CoreLabel
from kivy.uix.carousel import Carousel
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.image import Image, AsyncImage
from kivy.metrics import dp, sp
from kivy.utils import platform
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
from kivymd.uix.card import MDCard
from kivymd.uix.list import (
    OneLineAvatarIconListItem, ImageLeftWidget, IconRightWidget
)
from kivymd.uix.dialog import MDDialog
from kivy.uix.recycleview import RecycleView
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.list import MDList, OneLineAvatarListItem, ImageLeftWidget
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.selectioncontrol import MDCheckbox
from kivy.core.image import Image as CoreImage
from kivy.vector import Vector
from kivy.config import Config
from kivy.resources import resource_find
from kivy.graphics import Color, Ellipse
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelHeader
from kivy.uix.anchorlayout import AnchorLayout