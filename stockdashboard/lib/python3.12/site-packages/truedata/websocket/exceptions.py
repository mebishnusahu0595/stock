from colorama import Style, Fore    

class TDLiveCalcError(Exception):
    def __str__(self):
        return f"{Style.BRIGHT}{Fore.RED}Something's wrong with the live calculations- {self.args[0]}{Style.RESET_ALL}"

class TDLiveDataError(Exception):
    def __str__(self):
        return f"{Style.BRIGHT}{Fore.RED}Something's wrong with the live data- {self.args[0]}{Style.RESET_ALL}"

class TDInvalidRequestError(Exception):
    def __str__(self):
        return f"{Style.BRIGHT}{Fore.RED}Invalid request ({self.args[0]}){Style.RESET_ALL}"
