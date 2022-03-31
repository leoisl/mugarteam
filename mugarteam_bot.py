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


def get_chrome():
    chrome_options = Options()
    chrome_options.headless = False
    chrome_options.add_argument('--user-data-dir=user_data')
    driver = webdriver.Chrome("./chromedriver", options=chrome_options)
    driver.set_page_load_timeout(60)
    return driver


def send_whatsapp_messages(driver, group, messages, pngs):
  print("Sending whatsapp message...")
  actions = ActionChains(driver)
  driver.get("https://web.whatsapp.com")
  time.sleep(60)
  search_group_elem = driver.find_element(By.XPATH, "/html/body/div[1]/div[1]/div[1]/div[3]/div/div[1]/div/label/div/div[2]")
  search_group_elem.click()
  time.sleep(1)
  actions.send_keys(group).perform()
  time.sleep(1)
  actions.send_keys(Keys.ENTER).perform()
  time.sleep(5)
 
  for message, png in zip(messages, pngs):
    klembord.set({"image/png": png})
    time.sleep(1)
    actions.key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
    time.sleep(3)
    actions.send_keys(":robot").perform()
    time.sleep(1)
    actions.send_keys(Keys.ENTER).perform()
    time.sleep(1)
    actions.send_keys(message).perform()
    time.sleep(1)
    actions.send_keys(Keys.ENTER).perform()
    time.sleep(3)


def cleanup_chrome():
    subprocess.run("ps aux | grep chrome | awk '{print $2}' | xargs kill -9", shell=True)


def get_games():
  try:
    with open("games", "rb") as fh:
      games = pickle.load(fh)
  except:
    games = set()  
  return games

def save_games(games):
  with open("games", "wb") as fh:
    pickle.dump(games, fh)


dotabuff_ids = ["186071427", "390475173", "3012120", "86747675", "156879275", "28680095", "401036288", "17046675"]
def main():
  VPN_configs = initialize_VPN(area_input=["random countries europe 30"], skip_settings=1)
  while True:
    rotate_VPN(VPN_configs)
    games = get_games()
    driver = get_chrome()
    messages = []
    builds = []
    players = []

    print("Getting games...")
    for dotabuff_id in dotabuff_ids:
      try:
        driver.get(f"https://www.dotabuff.com/players/{dotabuff_id}/matches?date=week&enhance=overview")
        player = driver.find_element(By.XPATH, "/html/body/div[2]/div[2]/div[3]/div[3]/div[1]/div[1]/div[2]/h1").text.split("\n")[0]
        matches_table = driver.find_element(By.XPATH, "/html/body/div[2]/div[2]/div[3]/div[4]/section/section/article/table")
        all_trs = matches_table.find_elements(By.XPATH, ".//tr")[1:]
        for tr in all_trs:
          hero = tr.find_element(By.XPATH, "./td[2]/a[1]").text
          match = tr.find_element(By.XPATH, "./td[2]/a[1]").get_attribute("href").replace("https://", "")
          status = tr.find_element(By.XPATH, "./td[4]/a[1]").text
          status = "perdeu" if status == "Lost Match" else "ganhou"
          game_time = tr.find_element(By.XPATH, "./td[4]/div[1]/time").get_attribute("title").replace("+0000", "")
          game_mode = tr.find_element(By.XPATH, "./td[5]").text.replace("\n", " ")
          duration = tr.find_element(By.XPATH, "./td[6]").text
          kills = tr.find_element(By.XPATH, "./td[7]/span[1]/span[1]").text
          deaths = tr.find_element(By.XPATH, "./td[7]/span[1]/span[2]").text
          assists = tr.find_element(By.XPATH, "./td[7]/span[1]/span[3]").text
          game_description = f"{player} {status} um jogo {game_mode} de {hero}, KDA={kills}/{deaths}/{assists}. Duracao: {duration}. Horario: {game_time}. Link: {match}"
          if game_description not in games:
            games.add(game_description)
            messages.append(game_description)
            builds.append("https://"+match+"/builds")
            players.append(player)
      except Exception as exception:
         print(exception)

    actions = ActionChains(driver)
    pngs = []
    for player, build in zip(players, builds):
      driver.get(build)
      time.sleep(10)
      build_elem = driver.find_element(By.XPATH, f"//a[text()='{player}']/../../..")
      driver.execute_script("arguments[0].scrollIntoView(true);", build_elem)
      time.sleep(1)
      actions.send_keys(Keys.UP).perform()
      time.sleep(1)
      pngs.append(build_elem.screenshot_as_png)

    if len(messages)>0:
      print(f"Sending {len(messages)} games...")
      send_whatsapp_messages(driver, "Dota 2", messages, pngs)

    cleanup_chrome()
    save_games(games)

    print("Sleeping...")
    time.sleep(10*60)


main()

