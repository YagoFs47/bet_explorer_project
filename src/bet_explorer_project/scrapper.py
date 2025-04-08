from functools import partial
from selenium.common.exceptions import NoSuchElementException
import trio
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.chrome import ChromeDriverManager

from selenium.webdriver.firefox.service import Service
from selenium.webdriver.chrome.service import Service as ServiceC
from selenium.webdriver.common.by import By
from selenium.webdriver import Firefox, Chrome
from httpx import AsyncClient
from bs4 import BeautifulSoup
from bs4.element import Tag
from typing import List
import aiometer
import json
from bet_explorer_project.analisy_matchups import order_rounds, Matchup
import pandas as pd
from bet_explorer_project.settings import BASE_DIR

class Bot:
    b: Firefox
    windows: List
    is_rejectd_cookie = False
    all_matchups_bexp = []
    all_matchups_for_round_bexp = []
    all_matchups_fbref = []
    all_matchups_for_round_fbref= []


    def __init__(self, url, url_fbref, only_betexplorer=False):
        self.only_betexplorer = only_betexplorer
        self.all_matchups_bexp = []
        self.all_matchups_for_round_bexp = []
        self.all_matchups_for_round_bexp_dict = {}
        self.all_matchups_fbref = []
        self.all_matchups_for_round_fbref= []
        self.base_url = "https://www.betexplorer.com/"
        self.client = AsyncClient(base_url="https://www.betexplorer.com/")
        self.pages_in_use = []
        self.url = url
        self.url_fbref = url_fbref
        #cada etapa do código vai preenchendo essas lista aos poucos
        # que no final vai se tornar uma tabela excel.xlsx
        self.df_dict = {
                "rodada": [],
                "casa": [],
                "visitante": [],
                "placar": [],
                "casa_prob_win": [],
                "empate_prob_win": [],
                "fora_prob_win": [],
                "mercado": [],
                "over": [],
                "under": [],
                "xg_casa": [],
                "xg_fora": [],
            }
        self.df_dict_only_betexplorer = {
                "rodada": [],
                "casa": [],
                "visitante": [],
                "placar": [],
                "casa_prob_win": [],
                "empate_prob_win": [],
                "fora_prob_win": [],
                "mercado": [],
                "over": [],
                "under": [],
            }


    @classmethod
    def run_all(cls):
        with open(BASE_DIR / "project_betxplorer" /  "urls.json", "r") as file:
            json_data = json.load(file)
            for line in json_data["urls"]:
                url_bextp, url_fbref = line.split(";")
                Bot(url_bextp, url_fbref).run()

    def run(self):

        trio.run(self.get_all_matchups_data)

    def _get_page(self):
        for page in self.b.window_handles:
            if page not in self.pages_in_use:
                self.pages_in_use.append(page)
                return page

    def _drop_page(self, page):
        self.pages_in_use.remove(page)

    async def manager_get_odd(self, matchups_to_search: List[Matchup], **kwargs):
        
        data = await aiometer.run_all(
            [partial(self.get_odds_matchups, matchup) for matchup in matchups_to_search],
            max_at_once=5,
        )
        return data

    def formula_mais_proximo_2(self, data, mercado):
        over_abs = abs(
            float(data["over"].strip()) - 2
            )
        under_abs = abs(
            float(data["under"].strip()) - 2
            )
        data["result_calc"] = (over_abs + under_abs)
        data["mercado"] = float(mercado)
        return data.copy()
    
    def get_line_odd(self, group_of_lines: Tag, mercado):
        lines = group_of_lines.select("div.oddsComparisonAll__rowBookie")
        lines_data_pinnacle = None
        for line in lines:
            line_data = self.get_all_data_of_line(line)
            if line_data.get("casa").lower() == "pinnacle":
                lines_data_pinnacle = line_data.copy()
        else:
            if lines_data_pinnacle:
                return self.formula_mais_proximo_2(lines_data_pinnacle.copy(), mercado)
    
    def get_all_data_of_line(self, line: Tag) -> dict:
        over_s_only = line.select_one("div.over-s-only")
        odds_heads  = line.select_one("div.oddsComparisonAll__odds_heads ")
        over, under = [odd.text.replace("\xa0", "") for odd in odds_heads.select("div.oddsComparisonAll__odds")]
        return {"casa": over_s_only.text, "over": over, "under": under} 

    async def get_odds_matchups(self, matchup: Matchup):
        page = self._get_page()

        self.b.switch_to.window(page)
        self.b.get(self.base_url + matchup.url_matchup)

        await trio.sleep(2)


        #get odds 1x2
        self.b.switch_to.window(page)
        # self.b.execute_script(
        #     """
        #     document.querySelector('div#onetrust-consent-sdk').setAttribute('style', 'display: none;')
        #     """
        # ) 
        # if not self.is_rejectd_cookie: 
        #     self.b.find_element(By.CSS_SELECTOR, "#onetrust-reject-all-handler").click()
        #     self.is_rejectd_cookie = True
        
        # while True:
        #     try:
        #         _1_x_2_odd = self.b.find_element(By.CSS_SELECTOR, "#best-odds-0").text
        #         all_odds = _1_x_2_odd.split("\n")
        #         print(all_odds)
        #         print(f"output do '_1_x_2_odd' =>> \033[31m{_1_x_2_odd}\033 acaba aqui")
        #         casa, empate, visitante = _1_x_2_odd.split("\n")[13:]
        #         break
        #     except NoSuchElementException:
        #         print("erro em pegar as probabilidades") 
            
        #     except ValueError:
        #         casa, empate, visitante = _1_x_2_odd.split("\n")[-1].split()
        #         break
        
        #NOVA SOLUÇÃO
        while True:
            try:
                #PEGA A ULTIMA TR DA TABELA, OU SEJA A PINNACLE
                tr_pinnacle = self.b.find_elements(By.CSS_SELECTOR, "#best-odds-0 > tr")[-1]
                print(tr_pinnacle.text.split("\n"))
                casa, empate, visitante = tr_pinnacle.text.split("\n")[1:]
                break

            except NoSuchElementException:
                pass

            except ValueError:
                casa, empate, visitante = tr_pinnacle.text.split("\n")[-1].split("")
        
        #click no menu de odds na opção "over/under"
        await trio.sleep(2)
        self.b.switch_to.window(page)
        curl = self.b.current_url.split("/")[-2]
        print(curl)
        self.b.execute_script(f"match_change_bettype_best(1, '{curl}', 'ou', 'football', false, this, 'br'); return false;")

        # seleciona a opção de odds "Over/Under exibir todas as odds"
        await trio.sleep(2)
        self.b.switch_to.window(page)
        soup = BeautifulSoup(self.b.page_source, "html.parser")
        print(curl)
        odds_content_2 = soup.select_one("#odds-content-2")
        mercados = odds_content_2.select("div.oddsComparisonAll__fullTable")
        odds_content_2.select("div.oddsComparisonAll__content")
        odds_content = odds_content_2.select("div.oddsComparisonAll__content")

        mercados_analisados = []

        for mercado, odd in zip(mercados, odds_content):
            line_format_data = self.get_line_odd(odd, mercado.get("data-all-handicap"))
            if line_format_data:
                mercados_analisados.append(line_format_data)
        else:
            data = sorted(mercados_analisados, key=lambda dicionario: dicionario["result_calc"], reverse=False)[0]
            print(data)
            matchup.casa_prob_win = casa
            matchup.empate = empate
            matchup.fora_prob_win = visitante
            matchup.over = data.get("over")
            matchup.under = data.get("under")
            matchup.mercado = data.get("mercado")

        await trio.sleep(15)
        self._drop_page(page)

    def _gen_windows(self):
        for c in range(5):
            self.b.switch_to.new_window()

    def open_browser(self):
        service = ServiceC(executable_path=ChromeDriverManager().install())
        self.b = Chrome(service=service)

    def save_matchup(self, matchup: Matchup):
        if self.all_matchups_for_round_bexp_dict.get(matchup.round) != None: # rodada já cadastrada.
            self.all_matchups_for_round_bexp_dict[matchup.round]["matchups"].append(matchup)
            
        else: # primeiro cria a rodada, depois salva.
            self.all_matchups_for_round_bexp_dict[matchup.round] = {
                "rodada": matchup.round, 
                "matchups": [matchup]
                }

    def find_matchups_today(self, soup: BeautifulSoup) -> List[Matchup]:
        # identificar se o que eu to olhando é uma partida ou o cabeçalho da tabela
        table:Tag = soup.select_one("table.table-main")
        trs: List[Tag] = table.select("tr")
        headers = 0
        matchups = []

        last_round = 0
        for tr in trs: # para cada linha da tabela
            if tr.select_one("td.h-text-left"): # é partida
                home, away = tr.select_one("td.h-text-left").text.split('-') # pega o time de casa e visitante
                url_matchup = tr.select_one("td.h-text-center").select_one("a").get("href") # pega a url desse jogo
                score_home, score_away = [int(score) for score in tr.select_one("td.h-text-center").text\
                                        .replace(" AWA.", "")\
                                        .replace(" ABN.", "")\
                                        .replace("POSTP.", "0:0")\
                                        .split(':')] # pega o placar
                matchup = Matchup(
                    home,
                    away,
                    url_matchup,
                    score_home,
                    score_away,
                    round = last_round
                )
                #adiciona um matchup na lista de matchups para depois retornamos a lista
                matchups.append(matchup)
                self.save_matchup(matchup)

            else: # é o cabeçalho da partida
                round = tr.select_one("th.h-text-left").text
                last_round = int(round.split(".")[0].strip())
                headers += 1
            
        else:
            # with open("all_matchups_for_round_betextp.json", "w") as file:
            #     alt_matchups = list(reversed(self.all_matchups_for_round_bexp_dict.values()))
            #     json.dump(alt_matchups, file, indent=4)
            self.all_matchups_for_round_bexp = list(reversed(self.all_matchups_for_round_bexp_dict.values()))
            return matchups

    async def get_over_under_of_matchup(self, matchup: Matchup) -> List[float]:
        """
            Essa função pega as odds OVER & UNDER
            Apos pegas essas odds, serão feitos cálculos para aproximar a mais próxima de 2,
            Após achar essa odd, irá buscar informações desse mesmo jogo em outro site e pegar outras informações que
            serão descritas em outras funções
            :return [float, float]
        """

        respnse = await self.client.get(matchup.url_matchup)

    def save_matchup_fbref(self, data_matchup) -> None:
        self.all_matchups_fbref.append(data_matchup)
        if len(self.all_matchups_for_round_fbref) < int(data_matchup.get("game_week")):
            self.all_matchups_for_round_fbref.append(
                {
                    "rodada": int(data_matchup.get("game_week")), 
                    "matchups": [
                        Matchup.from_json(data_matchup)
                    ]
                }
            )
        else:
            self.all_matchups_for_round_fbref[int(data_matchup['game_week']) - 1]["matchups"].append(Matchup.from_json(data_matchup))
        
    def register_url(self, url, only_betxplorer=False):
        with open(BASE_DIR / "project_betxplorer" /  "urls.json", "r") as file:
            json_data = json.load(file)
            if not only_betxplorer:
                json_data["urls"].append(url)
            else:
                json_data["urls_only_betxplorer"].append(url)

        with open(BASE_DIR / "project_betxplorer" /  "urls.json", "w") as file:
            json.dump(json_data, file, indent=4)

    async def get_site_data(self, soup: BeautifulSoup) -> List[Matchup]:
        # identificar se o que eu to olhando é uma partida ou o cabeçalho da tabela
        div_table = soup.select_one("div.table_container")
        trs = div_table.select("tbody > tr")
        trs = list(filter(lambda tr: tr.get("class") == None, trs))

        for tr in trs:
            game_week = tr.select_one("th[data-stat='gameweek']").text
            score = tr.select_one("td[data-stat='score']").text
            home_team = tr.select_one("td[data-stat='home_team']").text
            away_team = tr.select_one("td[data-stat='away_team']").text
            xg_home_team = tr.select_one("td[data-stat='home_xg']").text
            xg_away_team = tr.select_one("td[data-stat='away_xg']").text
            data_matchup = {
                "game_week": game_week,
                "score": score,
                "home_team": home_team,
                "away_team": away_team,
                "xg_home_team": xg_home_team,
                "xg_away_team": xg_away_team,
                "url_matchup": self.url_fbref
            }
            # pprint(data_matchup)
            if score != '':
                self.save_matchup_fbref(data_matchup.copy())

        # else:
            # pprint(self.all_matchups)
            # with open("all_matchups_for_round_fbref.json", "w", encoding="utf-8") as file:
            #     json.dump(self.all_matchups_for_round_fbref, file, indent=4)

    async def get_all_matchups_data(self):
        async with trio.open_nursery() as nursery:
            
            if not self.only_betexplorer: # se for False, então vai incluir os dados da fbref nas buscas
                #fbref
                r_response = await self.client.get(self.url_fbref)
                soup = BeautifulSoup(r_response.text, "html.parser")
                await self.get_site_data(soup)

            # betexplorer
            r_response = await self.client.get(self.url)
            soup = BeautifulSoup(r_response.text, "html.parser")
            
            matchups = self.find_matchups_today(soup)

            # compara os jogos entre as rodadas para poder alinhar os dados da betexp com fbref
            # com estratégia de fuzzywuzzy passando cada rodada para a função order_rounds
            # Que vai ordenar as rodadas
            
            #abre um navegador para iniciar as buscas pelas odds
            self.open_browser()
            self._gen_windows()
            #inicia as buscar pelas odds dos jogos
            nursery.start_soon(self.manager_get_odd, matchups)

        self.b.quit()

        if not self.only_betexplorer: # se for falso, então vai incluir os dados da fbref nas buscas
            for round_betxp, round_fbref in zip(self.all_matchups_for_round_bexp, self.all_matchups_for_round_fbref):
                rodada_bextp_ordenada, rodada_fbref_ordenada = order_rounds(round_betxp, round_fbref)
                for team1, team2 in zip(rodada_bextp_ordenada["matchups"], rodada_fbref_ordenada["matchups"]):
                # na teoria, o que será mostrado aqui será duas instancias da class "Matchup"
                    self.df_dict['casa'].append(team1.home)
                    self.df_dict['visitante'].append(team1.away)
                    self.df_dict['placar'].append(f"{team1.home_score}-{team1.away_score}")

                    self.df_dict['xg_casa'].append(team2.home_xg)
                    self.df_dict['xg_fora'].append(team2.away_xg)

                    self.df_dict['rodada'].append(team2.round)
                    self.df_dict['casa_prob_win'].append(team1.casa_prob_win)
                    self.df_dict['empate_prob_win'].append(team1.empate)
                    self.df_dict['fora_prob_win'].append(team1.fora_prob_win)

                    self.df_dict['over'].append(team1.over)
                    self.df_dict['under'].append(team1.under)
                    self.df_dict['mercado'].append(team1.mercado)
        else:
            for round_betxp in self.all_matchups_for_round_bexp: # no contrário irá pegar somente os dados da betexplorer
                for team1 in round_betxp["matchups"]:
                    self.df_dict_only_betexplorer['casa'].append(team1.home)
                    self.df_dict_only_betexplorer['placar'].append(f"{team1.home_score}-{team1.away_score}")
                    self.df_dict_only_betexplorer['visitante'].append(team1.away)
                    self.df_dict_only_betexplorer['rodada'].append(team1.round)

                    self.df_dict_only_betexplorer['casa_prob_win'].append(team1.casa_prob_win)
                    self.df_dict_only_betexplorer['empate_prob_win'].append(team1.empate)
                    self.df_dict_only_betexplorer['fora_prob_win'].append(team1.fora_prob_win)

                    self.df_dict_only_betexplorer['over'].append(team1.over)
                    self.df_dict_only_betexplorer['under'].append(team1.under)
                    self.df_dict_only_betexplorer['mercado'].append(team1.mercado)


        league_name = self.url.split("/")[5: 7]
        if not self.only_betexplorer:
            df = pd.DataFrame(self.df_dict)
            df.to_excel(BASE_DIR / "project_betxplorer" / "ligas" / f"{'_'.join(league_name)}.xlsx")
            self.register_url(f"{self.url};{self.url_fbref}")
        else:
            df = pd.DataFrame(self.df_dict_only_betexplorer)
            df.to_excel(BASE_DIR / "project_betxplorer" / "ligas_only_betexplorer" / f"{'_'.join(league_name)}.xlsx")   
            self.register_url(f"{self.url}", self.only_betexplorer) 

def set_new_url(only_betexplorer=False):
    if not only_betexplorer:
        url = str(input("Digite uma nova url: "))
        # url = "https://www.betexplorer.com/br/football/england/premier-league/results/"
        url_fbref = str(input("Digite a url da fbref: ".upper()))
        # url_fbref = "https://fbref.com/pt/comps/9/cronograma/Premier-League-Resultados-e-Calendarios"
        bot = Bot(url, url_fbref).run()
    else:
        url = str(input("Digite uma nova url: "))
        print(only_betexplorer)
        bot = Bot(url, "", only_betexplorer=only_betexplorer).run()



def main():
    hash_map = {
        1: Bot.run_all,
        2: set_new_url,
        3: partial(set_new_url, only_betexplorer=True)
    }
    while True:
        command = int(input(
    """SELECIONE UMA OPÇÃO:
    [1] REFRESH ALL
    [2] ADD NEW_LEAGUE
    [3] ONLY BETXPLORER

    SELECT:  
    """))
        hash_map[command]()
        
main()


