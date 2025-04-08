from fuzzywuzzy.fuzz import partial_token_sort_ratio, partial_token_set_ratio
from typing import List, Optional, Self, Dict
from colorama import Fore, init
from random import choice

init()


class Matchup:
    home: str
    away: str
    url_matchup: str
    home_score: str
    away_score: str
    round: int
    away_xg: Optional[int]
    home_xg: Optional[int]
    casa_prob_win: Optional[float]
    empate: Optional[float]
    fora_prob_win: Optional[float]
    over: Optional[float]
    under: Optional[float]
    mercado: Optional[float]
    

    def __init__(
            self, 
            home, 
            away, 
            url_matchup, 
            home_score, 
            away_score, 
            round, 
            away_xg=None, 
            home_xg=None,
            casa_prob_win=None,
            empate=None,
            fora_prob_win=None,
            over=None,
            under=None,
            mercado=None,
            ):
        self.home = home
        self.away = away
        self.url_matchup = url_matchup
        self.home_score = home_score
        self.away_score = away_score
        self.round = round
        self.away_xg = away_xg
        self.home_xg = home_xg
        self.casa_prob_win = casa_prob_win
        self.empate = empate
        self.fora_prob_win = fora_prob_win
        self.over = over
        self.under = under
        self.mercado = mercado

    def __repr__(self):
        return f"""{self.home} ({self.home_score}:{self.away_score}) {self.away} | rodada: {self.round} | over: {self.over} | under: {self.under}"""

    def __eq__(self, value):
        percent = partial_token_set_ratio(s1=f"{self.home}{self.away}", s2=f"{value.home}{value.away}")
        # print(False, percent, f"{Fore.GREEN}{self}{Fore.RESET}", f"{Fore.RED}{value}{Fore.RESET}")
        return percent

    def to_json(self):
        return {
            "home": self.home,
            "away": self.away,
            "home_score": self.home_score,
            "away_score": self.away_score,
            "round": self.round
            }

    @classmethod
    def from_json(cls, data):
        matchup = Matchup(
            round=data["game_week"],
            home_score=int(data["score"].split("–")[0]),
            away_score=int(data["score"].split("–")[1]),
            away=data["away_team"],
            home=data["home_team"],
            away_xg=data["xg_away_team"],
            home_xg=data["xg_home_team"],
            url_matchup=data["url_matchup"]
        )
        return matchup

def order_rounds(rodada_betextp: Dict[int, List[Matchup]], rodada_fbref: Dict[int, List[Matchup]]):
    """Essa função vai receber a rodada na betxplorer e fbref"""
    colors = [Fore.GREEN, Fore.BLUE, Fore.RED, Fore.CYAN, Fore.YELLOW, Fore.MAGENTA]
    print("-= -= -= -= -= -= Antes de ordenar =- =- =- =- =- =- =-")
    for matchup_betxp, matchup_fbref, index_zip in zip(rodada_betextp['matchups'], rodada_fbref['matchups'], range(len(rodada_betextp['matchups']))):
        color = choice(colors)
        print(f"{color}{matchup_betxp=}{Fore.RESET} |||||| {color}{matchup_fbref=}{Fore.RESET}")
        maior_porcentagem = {"porcentagem": 0, "indice": 0}
        for i, matchup_betxp2 in enumerate(rodada_betextp["matchups"]):
            eq = (matchup_fbref == matchup_betxp2)
            if eq > maior_porcentagem['porcentagem']:
                maior_porcentagem['porcentagem'] = eq
                maior_porcentagem["indice"] = i
        else:
            #strong = [matchup2, matchup3, matchup1]
            #strong = [matchup1, matchup3, matchup2]
            #correct = [matchup1, matchup2, matchup3]
            matchup_incorrect = rodada_betextp.get("matchups")[index_zip]
            matchup_correct = rodada_betextp.get('matchups')[maior_porcentagem['indice']]
            if [matchup_correct.home_score, matchup_correct.away_score] == [matchup_fbref.home_score, matchup_fbref.away_score]:
                rodada_betextp.get("matchups")[index_zip] = matchup_correct
                rodada_betextp.get("matchups")[maior_porcentagem['indice']] = matchup_incorrect
    
    print("-= -= -= -= -= -= Depois de ordenar =- =- =- =- =- =- =-")
    for matchup_betxp, matchup_fbref, index_zip in zip(rodada_betextp['matchups'], rodada_fbref['matchups'], range(len(rodada_betextp['matchups']))):
        color = choice(colors)
        print(f"{color}{matchup_betxp=}{Fore.RESET} |||||| {color}{matchup_fbref=}{Fore.RESET}")

    return rodada_betextp, rodada_fbref

