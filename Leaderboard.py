import requests
import telebot
import threading
import TgBot
import time
from Person  import User
from Person import Position
from Person import Bet
from collections import defaultdict
try:
    LeaderboardURL = "https://www.binance.com/bapi/futures/v2/public/future/leaderboard/getOtherLeaderboardBaseInfo"
    PositionsURL = "https://www.binance.com/bapi/futures/v1/public/future/leaderboard/getOtherPosition"

    LeaderboardPayload = {"encryptedUid":"!"}
    UserPayload = {"encryptedUid":"!","tradeType":"PERPETUAL"}  

    def GetLeaderboardData(encryptedId):
        usrPyaload = UserPayload
        usrPyaload["encryptedUid"] = encryptedId
        while(True):
            try:
                req = requests.post(url = LeaderboardURL, json = usrPyaload)
                responseJson = req.json()
                return responseJson
            except requests.exceptions.RequestException as e:
                time.sleep(10)
            

    def GetPositionsData(encryptedId):
        while(True):
            try:
                usrPyaload = UserPayload
                usrPyaload["encryptedUid"] = encryptedId
                req = requests.post(url = PositionsURL, json = usrPyaload)
                responseJson = req.json()
                return responseJson
            except Exception as e:
                time.sleep(10)
        

    FirstTime = True
    Users = []
    Bets = []

    t1 = threading.Thread(target=TgBot.Polling)
    t1.start()
    
    def GetUserByName(id):
        for item in Users:
            if item.id == id:
                return item
        return None

    def IfPositionExists(usr, givenPosition):
        found = False
        
        for position in usr.Positions:
            if givenPosition == position:
                found = True
                break
        
        return found

    def GetPosition(data):
        symbol = data["symbol"]
        entryPrice = data["entryPrice"]
        markPrice = data["markPrice"]
        pnl = float("{:.2f}".format(data["pnl"]))
        roe = float("{:.4f}".format(data["roe"]))*100
        updateTime = data["updateTimeStamp"]
        leverage = data["leverage"]
        amount = data["amount"]
        positionTerm = ""
        if pnl == 0 or roe == 0 or entryPrice == markPrice:
            return None
        if (entryPrice < markPrice and pnl > 0) or (entryPrice > markPrice and pnl < 0):
                positionTerm = "LONG🟢"
        elif(entryPrice > markPrice and pnl > 0) or (entryPrice < markPrice and pnl < 0):
                positionTerm = "SHORT🔴"
        else:
            print("WHY")
        positionToIns = Position(symbol,entryPrice,markPrice,float(pnl),float(roe),updateTime, positionTerm,leverage,amount)
        return positionToIns       

    def GetAbsPosition(data):
        symbol = data["symbol"]
        entryPrice = float("{:.3f}".format(data["entryPrice"]))
        markPrice = float("{:.3f}".format(data["markPrice"]))
        pnl = float("{:.2f}".format(data["pnl"]))
        roe = float("{:.2f}".format(data["roe"]))*100
        updateTime = data["updateTimeStamp"]
        leverage = data["leverage"]
        amount = data["amount"]
        positionTerm = ""

        positionToIns = Position(symbol,entryPrice,markPrice,float(pnl),float(roe),updateTime, positionTerm,leverage,amount)
        return positionToIns  

    def CheckIfClosed(usr, positions):
        numRes = []
        for item in positions:
            positionToIns = GetAbsPosition(item)
            if(positionToIns == None):
                continue
            numRes.append(positionToIns)

        for position in usr.Positions:
            if position not in numRes:
                for b in Bets:
                    if position.symbol == b.symbol:
                        print('Close Bet ' + position.symbol)
                        TgBot.SendAllUsers1(usr, position)
                        Bets.remove(b)
                        break
                print('CLOSE ' + usr.name +' ' + position.symbol +' ' + position.term)
                usr.Positions.remove(position)

    while(True):
        usersData = TgBot.GetAllUsers()
        for item in usersData:
            tmpUser = GetUserByName(item)
            usData = GetLeaderboardData(item)
            if usData == None:
                continue
            if usData["data"] == None:
                continue
            if tmpUser == None:
                tmpUser = User(usData["data"]["nickName"], item,[])
                Users.append(tmpUser)

            userData = GetPositionsData(tmpUser.id)
        
            if userData["data"]["otherPositionRetList"] == None:
                continue

            for data in userData["data"]["otherPositionRetList"]:
                positionToIns = GetPosition(data)
                if(positionToIns == None):
                 continue
                if IfPositionExists(tmpUser,positionToIns) == False:
                    tmpUser.Positions.append(positionToIns)
                    flag = True
                    if positionToIns.term == 'LONG🟢':
                        flag = True
                    else:
                        flag = False
                    b = Bet(positionToIns.symbol,flag)
                    if  b not in Bets:
                        Bets.append(b)
                        TgBot.SendAllUsers(tmpUser,positionToIns)
                    print('NEW '+tmpUser.name +' ' + positionToIns.symbol +' ' + positionToIns.term)

                else:
                    for position in tmpUser.Positions:
                        if positionToIns == position:
                            position.markPrice = data["markPrice"]
                            position.pnl = float("{:.2f}".format(data["pnl"]))
                            position.roe = float("{:.4f}".format(data["roe"]))*100
                            if(position.amount != data["amount"]):
                                position.amount = data["amount"]
                                TgBot.SendAllUsersChange(tmpUser,position,"Amount")
                            if(position.leverage != data["leverage"]):
                                position.leverage = data["leverage"]
                                TgBot.SendAllUsersChange(tmpUser,position,"Leverage")
                            break

            CheckIfClosed(tmpUser,userData["data"]["otherPositionRetList"])

except Exception as e:
    logf = open("logger.log", "w")
    logf.write("Failed : {0}\n".format(str(e)))
    # TgBot.SendError("Failed : {0}\n".format(str(e)))
