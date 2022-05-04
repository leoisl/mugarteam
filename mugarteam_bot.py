#!/usr/bin/python3.8

import time
from functools import partial
from urllib.parse import quote
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
import subprocess
import random
import pickle
from selenium.common.exceptions import NoSuchElementException
import klembord
from nordvpn_switcher import initialize_VPN, rotate_VPN
import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict
import sys



dotabuff_ids = ["186071427", "390475173", "3012120", "86747675", "156879275", "28680095", "401036288", "17046675" ,"133325943", "358448092", "62545102", "172840436"]
def get_chrome():
    print("Getting selenium chrome...")
    chrome_options = Options()
    chrome_options.headless = False
    chrome_options.add_argument('--user-data-dir=user_data')
    driver = webdriver.Chrome("./chromedriver", options=chrome_options)
    driver.set_page_load_timeout(60)
    return driver


def send_whatsapp_messages(driver, group, messages, pngs=None):
  print("Opening whatsapp...")
  actions = ActionChains(driver)
  while True:
    try:
      driver.get("https://web.whatsapp.com")
      time.sleep(60)
      print("Locating group...")
      search_group_elem = driver.find_element(By.XPATH, "//div[@title='Search input textbox']")
      search_group_elem.click()
      time.sleep(1)
      actions.send_keys(group).perform()
      time.sleep(1)
      actions.send_keys(Keys.ENTER).perform()
      time.sleep(5)
      break
    except:
      pass
    
  if pngs is None:
    pngs = [None] * len(messages)
  for message, png in zip(messages, pngs):
    print("Sending whatsapp message...")
    if png is not None:
        klembord.set({"image/png": png})
        time.sleep(1)
        actions.key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
        time.sleep(5)
    actions.send_keys(":robot").perform()
    time.sleep(3)
    actions.send_keys(Keys.ENTER).perform()
    time.sleep(1)
    actions.send_keys(message).perform()
    time.sleep(1)
    actions.send_keys(Keys.ENTER).perform()
    time.sleep(5)
  
  print("Waiting before closing whatsapp...")
  time.sleep(60)


def cleanup_chrome():
    print("Cleaning up chrome...")
    subprocess.run("ps aux | grep chrome | awk '{print $2}' | xargs kill -9", shell=True)


def get_games():
  print("Loading games...")
  try:
    with open("games", "rb") as fh:
      games = pickle.load(fh)
  except:
    games = set()  
  return games

def save_games(games):
  print("Saving games...")
  with open("games", "wb") as fh:
    pickle.dump(games, fh)

@dataclass(frozen=True)
class Game:
    dotabuff_id: str
    player: str
    hero: str
    match: str
    won: bool
    game_time: datetime
    game_mode: str
    duration: str
    kills: int
    deaths: int
    assists: int

    def __eq__(self, other):
        return (self.dotabuff_id, self.match)== (other.dotabuff_id, other.match)

    def __hash___(self):
        return hash(self.dotabuff_id, self.match)

    @property
    def won_as_str(self):
        return "ganhou" if self.won else "perdeu"

    def get_game_description(self):
        return f"{self.player} {self.won_as_str} com {self.hero} ({self.kills}/{self.deaths}/{self.assists}) em {self.game_time.strftime('%d/%m/%Y %H:%M:%S')}: {self.match}"

    def get_game_build(self):
        return f"https://{self.match}/builds"

def get_last_monday():
    today = datetime.today()
    last_monday = today - timedelta(days=today.weekday())
    last_monday = last_monday.replace(hour=12, minute=0, second=0, microsecond=0)
    return last_monday

def get_players_sorted_by_ranking(games):
    player_to_games = defaultdict(list)
    players = set()
    for game in games:
        last_monday = get_last_monday()
        game_should_be_counted = (game.game_time - last_monday).total_seconds() > 0
        if game_should_be_counted:
            player_to_games[game.player].append(game)
            players.add(game.player)
    player_wins_losses = [(player, sum(int(game.won) for game in player_to_games[player]), sum(int(not game.won) for game in player_to_games[player])) for player in players]
    player_wins_losses = sorted(player_wins_losses, key=lambda player_wins_losses_tuple: player_wins_losses_tuple[1]-player_wins_losses_tuple[2], reverse=True)
    return player_wins_losses


def format_ranking(player_wins_losses):
    lines = ["Ranking semanal:"]
    for index, (player, wins, losses) in enumerate(player_wins_losses):
        lines.append(f"{index+1}. {player}: {(wins-losses):+d} pontos ({wins} vitorias, {losses} derrotas)")
    return "\n".join(lines)


def main(args):
  if args.show_ranking:
    games = get_games()
    player_wins_losses = get_players_sorted_by_ranking(games)
    ranking = (format_ranking(player_wins_losses))
    print(ranking)
    return

  if not args.no_vpn:
    VPN_configs = initialize_VPN(area_input=["random countries europe 30"], skip_settings=1)
  for iteration in range(10000000):
    if not args.no_vpn:
        need_rotation = iteration%100==0
        if need_rotation:
            print("Rotating VPN...")
            rotate_VPN(VPN_configs)
    driver = get_chrome()    
    if args.config_browser:
        print("Configuring browser...")
        print("Quit tool when done...")
        time.sleep(100000000)


    games = get_games()
    games_to_report = []
    print("Looking for new games...")
    for dotabuff_id in dotabuff_ids:
      print(f"Looking for games with id {dotabuff_id}...")
      try:
        driver.get(f"https://www.dotabuff.com/players/{dotabuff_id}/matches?date=week&enhance=overview")
      except Exception:
        pass

      try:
        player = driver.find_element(By.XPATH, "/html/body/div[2]/div[2]/div[3]/div[3]/div[1]/div[1]/div[2]/h1").text.split("\n")[0]
        matches_table = driver.find_element(By.XPATH, "/html/body/div[2]/div[2]/div[3]/div[4]/section/section/article/table")
        all_trs = matches_table.find_elements(By.XPATH, ".//tr")[1:]
        for tr in all_trs:
          hero = tr.find_element(By.XPATH, "./td[2]/a[1]").text
          match = tr.find_element(By.XPATH, "./td[2]/a[1]").get_attribute("href").replace("https://", "")
          status = tr.find_element(By.XPATH, "./td[4]/a[1]").text
          won = status == "Won Match"
          game_time = tr.find_element(By.XPATH, "./td[4]/div[1]/time").get_attribute("title").replace("+0000", "").strip()
          game_time = datetime.strptime(game_time, "%a, %d %b %Y %H:%M:%S")
          game_mode = tr.find_element(By.XPATH, "./td[5]").text.replace("\n", " ")
          duration = tr.find_element(By.XPATH, "./td[6]").text
          kills = tr.find_element(By.XPATH, "./td[7]/span[1]/span[1]").text
          deaths = tr.find_element(By.XPATH, "./td[7]/span[1]/span[2]").text
          assists = tr.find_element(By.XPATH, "./td[7]/span[1]/span[3]").text
          game = Game(dotabuff_id, player, hero, match, won, game_time, game_mode, duration, kills, deaths, assists)
          if game not in games:
            games.add(game)
            games_to_report.append(game)
      except Exception as exception:
        print(exception)
      finally:
        pass

    get_images_and_send_message = iteration > 0 or not args.just_update_DB_in_first_it
    if get_images_and_send_message:
        print("Getting matches images...")
        actions = ActionChains(driver)
        pngs = []
        for game in games_to_report:
          print(f"Getting image for match {game.get_game_build()}")
          while True:
            try:
              driver.get(game.get_game_build())
              time.sleep(10)
              build_elem = driver.find_element(By.XPATH, f"//a[text()='{game.player}']/../../..")
              driver.execute_script("arguments[0].scrollIntoView(true);", build_elem)
              time.sleep(2)
              actions.send_keys(Keys.UP).perform()
              time.sleep(2)
              pngs.append(build_elem.screenshot_as_png)
              break
            except Exception as exception:
              print(exception)    

        if len(games_to_report)>0:
          print(f"Sending {len(games_to_report)} games...")
          messages = list(map(lambda game: game.get_game_description(), games_to_report))
          send_whatsapp_messages(driver, "Dota 2", messages, pngs)
    else:
        print("Skipping getting images and sending whatsapp messages...")

    if args.send_ranking and iteration==0:
        player_wins_losses = get_players_sorted_by_ranking(games)
        ranking = (format_ranking(player_wins_losses))
        send_whatsapp_messages(driver, "Dota 2", [ranking])


    cleanup_chrome()
    save_games(games)

    print(f"Sleeping (iteration {iteration})...")
    time.sleep(10*60)


parser = argparse.ArgumentParser(description='Mugarteam dota 2 bot.')
parser.add_argument('-c', '--config-browser', action="store_true", default=False,
    help='Just open the browser and waits for a long time for you to config with whatever you want.')
parser.add_argument('-u', '--just-update-DB-in-first-it', action="store_true", default=False,
    help='For the first run, just update the games database (do not get matches images nor send whatsapp messages)')
parser.add_argument('--no-vpn', action="store_true", default=False,
    help='Dont use vpn')
parser.add_argument('-r', "--send-ranking", action="store_true", default=False,
    help='Send ranking')
parser.add_argument('-s', "--show-ranking", action="store_true", default=False,
    help='Show ranking and exits')
args = parser.parse_args()
main(args)

