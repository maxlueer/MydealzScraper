#!/usr/bin/python
# coding=utf-8

'''
The MIT License (MIT)
Copyright (c) 2015 Roy Freytag
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''

import datetime
import json
import os
import re
import requests
import sys
import telebot
import threading
import time
import traceback

from bs4 import BeautifulSoup as bs
from contextlib import suppress
from colorama import init, Fore, Back, Style
from emoji import emojize
#from pyshorteners import Shortener
from threading import Thread

# Emoji definitions
wave = emojize(":wave:", use_aliases=True)
hot = emojize(":fire:", use_aliases=True)
free = emojize(":free:", use_aliases=True)
wish = emojize(":star:", use_aliases=True)

# Basic stuff
os.chdir(os.path.dirname(os.path.realpath(__file__)))
init(autoreset=True) # Colorama
#shortener = Shortener("Isgd")
header = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36 OPR/55.0.2994.61"}

# Get settings from file
def get_settings():
    global debug_mode; global short_url; global telegram
    global sleep_time; global tg_token; global tg_token_priority
    global tg_cid; global tg_cid2

    debug_mode = 0
    short_url = 0
    telegram = 0

    settings = {}
    exec(open("./settings.txt").read(), None, settings)
    if settings["debug_mode"]:
        debug_mode = 1
    if settings["short_url"]:
        short_url = 1
    if settings["telegram"]:
        telegram = 1
    sleep_time = settings["sleep_time"]
    tg_token = settings["tg_token"]
    tg_token_priority = settings["tg_token_priority"]
    tg_cid = settings["tg_cid"]
    tg_cid2 = settings["tg_cid2"]

get_settings()

# Debug mode
def debug(text):	
    if debug_mode:
    	print(Fore.YELLOW + "DEBUG: " + text)
    return 0

# Get already found deals from file
def get_found():
    global found_deals; global found_deals2
    found_deals = [line.rstrip("\n") for line in open ("./found_{}.txt".format(tg_cid))]
    found_deals2 = [line.rstrip("\n") for line in open ("./found_{}.txt".format(tg_cid2))]

# Get wanted articles from file
def get_wanted():
    global wanted_articles; global wanted_articles2
    wanted_articles = [line.rstrip("\n") for line in open ("./wanted_{}.txt".format(tg_cid))]
    print(Fore.CYAN + "User 1: Suche nach Deals fuer: " + str(wanted_articles).replace("[", "").replace("]", ""))
    wanted_articles2 = [line.rstrip("\n") for line in open ("./wanted_{}.txt".format(tg_cid2))]
    print(Fore.CYAN + "User 2: Suche nach Deals fuer: " + str(wanted_articles2).replace("[", "").replace("]", ""))

# Link processing
def process_link(link):
    #try:
        #proc_link = shortener.short(link)
    #except:
    #   print("Shortener-Service nicht erreichbar. Verwende vollen Link.")
        #proc_link = link
    return link
    
# Telegram bot
bot = telebot.TeleBot(tg_token)
bot_priority = telebot.TeleBot(tg_token_priority)

@bot.message_handler(commands=["hello"])
def hello(msg):
    cid = msg.chat.id
    bot.send_message(cid, "Hi! " + wave + " Ich bin noch da, keine Sorge.")

@bot.message_handler(commands=["add"])
def add_item(msg):
    cid = msg.chat.id
    with open("./wanted_{}.txt".format(cid), "a") as f:
        f.write(msg.text.replace("/add ", "") + "\n")
    bot.send_message(cid, "Schlagwort wurde der Liste hinzugefügt.")

@bot.message_handler(commands=["remove"])
def remove_item(msg):
    cid = msg.chat.id
    with open("./wanted_{}.txt".format(cid), "r") as list:
        lines = list.readlines()
    with open("./wanted_{}.txt".format(cid), "w") as remove:
        for line in lines:
            if line.lower() != (msg.text.replace("/remove ", "") + "\n").lower():
                remove.write(line)
    bot.send_message(cid, "Schlagwort wurde von der Liste entfernt.")

@bot.message_handler(commands=["reset"])
def reset_found(msg):
    cid = msg.chat.id
    open("./found_{}.txt".format(cid), "w").close()
    bot.send_message(cid, "Liste der gefundenen Deals wurde geleert.")
    get_found()

@bot.message_handler(commands=["list"])
def list_items(msg):
    cid = msg.chat.id
    with open("./wanted_{}.txt".format(cid), "r") as list:
        lines = list.readlines()
    bot.send_message(cid, "Suche nach Deals für: " + str(lines).replace("[", "").replace("]", "")) # fix \n

def telegram_bot():
    while True:
        try:
            bot.polling(none_stop=True)
        except:
            debug(traceback.format_exc())
            time.sleep(5)

# Scraping routine
def scrape(url, type):
    try:
        #debug("Scraping " + type + " deals")
        site = requests.get(url, headers=header, timeout=20)
        soup = bs(site.content, "lxml")
        debug("Request completed")

        listings = soup.find_all("article", {"id":re.compile("thread_.*")})
        if listings is None:
            print("Keine Listings gefunden. Seite geändert?")

        for thread in listings:
            info = thread.find("a", class_="cept-tt thread-link linkPlain thread-title--list")
            dealid = thread.attrs["id"]
            if dealid in found_deals:
                debug("Deal already found " + dealid)
                continue
            title = info.string.strip()
            link = info.get("href")

            if short_url:
                proc_link = process_link(link)
            else:
                proc_link = link

            # print("[" + type + "] %s: %s" % (re.sub(r"[^\x00-\x7F]+"," ", title), proc_link))
            print("[" + "] %s: %s" % (re.sub(r"[^\x00-\x7F]+"," ", title), proc_link))
            if telegram:
                emoji = free
                if type == hot:
                    emoji = hot
                    
                bot.send_message(tg_cid, emoji + " %s: %s" % (title, proc_link), disable_web_page_preview=True)
                time.sleep(5)
                bot.send_message(tg_cid2, emoji + " %s: %s" % (title, proc_link), disable_web_page_preview=True)

            with open("./found_{}.txt".format(tg_cid), "a") as found:
                found.write(dealid + "\n")
            get_found()
            time.sleep(4)
        #debug("Scraping " + type + " deals complete")
    except:
        debug(traceback.format_exc())
        time.sleep(60)

# User wanted scraping routine
def scrape_wanted(tg_cid, found_deals, articles, wanted_articles):
    for wanted_item in wanted_articles:
        deals = articles.find_all("a", string=re.compile("(?i).*("+wanted_item+").*"), class_="cept-tt thread-link linkPlain thread-title--list")
        for thread in deals:
            dealid = articles.attrs["id"]
            if dealid in found_deals:
                debug("Deal already found " + dealid)
                continue
            title = thread.string.strip()
            link = thread.get("href")

            if short_url:
                proc_link = process_link(link)
            else:
                proc_link = link

            print("[WANT] %s: %s" % (re.sub(r"[^\x00-\x7F]+"," ", title), proc_link))
            if telegram:
                bot_priority.send_message(tg_cid, wish + " %s: %s" % (title, proc_link), disable_web_page_preview=True)
            with open("./found_{}.txt".format(tg_cid), "a") as found:
                found.write(dealid + "\n")
            get_found()
            time.sleep(4)

# Hottest deals scraping routine
def scrape_hottest():
    try:
        debug("Fetching json for hottest deals")
        json_url = requests.get("https://www.mydealz.de/widget/hottest?selectedRange=day&threadTypeTranslated=&merchant_name=&merchant_id=&eventId=&groupName=&context=listing", headers=header, timeout=20)
        json_data = json_url.json()
        debug("Request completed")        
        
        for thread in json_data["data"]["threads"]:
            title = thread["title"].strip()
            link = thread["url"]
            if short_url:
                proc_link = process_link(link)
            else:
                proc_link = link
            dealid = "hot_" + str(thread["id"])
            if dealid in found_deals:
                debug("Deal already found " + dealid)
                continue

            print("[" + "] %s: %s" % (re.sub(r"[^\x00-\x7F]+"," ", title), proc_link))
            if telegram:
                bot_priority.send_message(tg_cid, hot + " %s: %s" % (title, proc_link), disable_web_page_preview=True)
                bot_priority.send_message(tg_cid2, hot + " %s: %s" % (title, proc_link), disable_web_page_preview=True)
                time.sleep(5)

            with open("./found_{}.txt".format(tg_cid), "a") as found:
                found.write(dealid + "\n")
            get_found()
            time.sleep(4)
        debug("Processing hottest deals complete")
    except:
        debug(traceback.format_exc())
        time.sleep(60)

# MyDealz scraper
def mydealz_scraper():
    while True:
        # Wanted scraper
        try:
            debug("Scraping for wanted items")
            site = requests.get("https://www.mydealz.de/new?page=1", headers=header, timeout=20)
            soup = bs(site.content, "lxml")
            debug("Request completed")

            listings = soup.find_all("article", {"id":re.compile("thread_.*")})
            if listings is None:
                print("Keine Listings gefunden. Seite geändert?")

            for articles in listings:
                scrape_wanted(tg_cid, found_deals, articles, wanted_articles)
                scrape_wanted(tg_cid2, found_deals2, articles, wanted_articles2)
                
            debug("Scraping for wanted items complete")
        except:
            debug(traceback.format_exc())
            time.sleep(60)
        
        # Hottest today scraper
        #scrape_hottest()
        
        # Hot deals scraper
        #scrape("https://www.mydealz.de/hot?page=1", hot)
        
        # Freebie scraper
        #scrape("https://www.mydealz.de/gruppe/freebies-new?page=1", free)
        
        debug("Now sleeping until next cycle")
        time.sleep(sleep_time)

if __name__=="__main__":
    # Check for required files
    with suppress(Exception):
        open("./wanted_{}.txt".format(tg_cid), "x")
    with suppress(Exception):
        open("./found_{}.txt".format(tg_cid), "x")
    with suppress(Exception):
        open("./wanted_{}.txt".format(tg_cid2), "x")
    with suppress(Exception):
        open("./found_{}.txt".format(tg_cid2), "x")

    # Initial fetch
    get_wanted()
    get_found()

    Thread(target = telegram_bot).start()
    Thread(target = mydealz_scraper).start()
