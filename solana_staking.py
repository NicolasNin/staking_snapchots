import asyncio
from pandas.io.json import json_normalize
from solana.publickey import PublicKey
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solana.rpc.types import MemcmpOpts
import requests
import json
import pandas as pd
import datetime
#https://stackoverflow.com/questions/70163352/am-i-able-to-get-a-list-of-delegators-by-validator-solana-using-the-json-rpc-a
STAKE_PROGRAM_ID: PublicKey = PublicKey("Stake11111111111111111111111111111111111111")


async def getStakingValidator(validator_pubkey = "C6RzXrzqXewJ5xsYpYPmveHh7A2UUkP1932FArXRSAzE"):
    client = AsyncClient("https://api.mainnet-beta.solana.com", Confirmed)
    print("Connecting...")
    await client.is_connected()

    #this create a filter on the validator address
    #https://docs.solana.com/developing/clients/jsonrpc-api#getprogramaccounts

    memcmp_opts = [MemcmpOpts(offset=124, bytes=validator_pubkey)] # put the pubkey of the validator vote address here
    response = await client.get_program_accounts(
        STAKE_PROGRAM_ID,
        encoding="jsonParsed",
        data_size=200,
        memcmp_opts=memcmp_opts
    )

    await client.close()
    return response["result"]


def getInflationRewards(address_list,epoch):
    url = "https://api.mainnet-beta.solana.com"
    headers = {'Content-Type': 'application/json'}


    payload = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "getInflationReward",
    "params": [
        address_list, {"epoch": epoch}
    ]
    }


    response = requests.post(url, data=json.dumps(payload),headers=headers).json()
    return response["result"]

def getAllInflationRewards(address_list,epoch_range):
    all_data={add:{"totalAmount":0} for add in address_list}
    for epoch in epoch_range:
        print("getting reward for epoch",epoch)
        data = getInflationRewards(address_list,epoch)
        for i,add in enumerate(address_list):
            if data[i] is not None:
                amount = data[i]["amount"]
                all_data[add].update({
                    "amount"+str(epoch):amount,
                    "postBalance"+str(epoch):data[i]["postBalance"]
                            })
                all_data[add]["totalAmount"]+=amount
    return all_data

async def getCurentEpoch():
    client = AsyncClient("https://api.mainnet-beta.solana.com", Confirmed)
    curentEpoch = await client.get_epoch_info()
    return curentEpoch["result"]["epoch"]

if __name__ == "__main__":
    stakeDao_pubkey = "C6RzXrzqXewJ5xsYpYPmveHh7A2UUkP1932FArXRSAzE"
    validator_data = asyncio.run(getStakingValidator(stakeDao_pubkey))
    df = json_normalize(validator_data)

    #https://docs.solana.com/staking/stake-accounts
    #voter should be stakeDAO pubkey    
    df["voter"]=df["account.data.parsed.info.stake.delegation.voter"]
    #staker and withdrawer are two account handling the staking, often the same, withdrawer has more power 
    df["staker"]=df["account.data.parsed.info.meta.authorized.staker"]
    df["withdrawer"] = df["account.data.parsed.info.meta.authorized.withdrawer"]

    # this is meaningful when  stake accounts have a lockup, we dont really care about this 
    # here just to understand all the properties
    df["custodian"]=df["account.data.parsed.info.meta.lockup.custodian"]
    df["lockupTimestamp"] =df["account.data.parsed.info.meta.lockup.unixTimestamp"]
    columns_accounts=["voter","staker","withdrawer","custodian"]
    df["stake"] = df["account.data.parsed.info.stake.delegation.stake"].astype(int)
    df["stakeActivationEpoch"] = df["account.data.parsed.info.stake.delegation.activationEpoch"].astype(int)
    df["stakeDeactivationEpoch"] = df["account.data.parsed.info.stake.delegation.deactivationEpoch"].apply(lambda x:int(x))
    df["creditObserved"] = df["account.data.parsed.info.stake.creditsObserved"]
    df["warmupCoolDownRate"] = df["account.data.parsed.info.stake.delegation.warmupCooldownRate"]
    df["balance"] =  df["account.lamports"].astype(int)

    columns = ["pubkey","withdrawer","staker","stake","stakeActivationEpoch","stakeDeactivationEpoch","balance"]
    df2 = df[columns].copy()
    df2 = df2.set_index("pubkey")
    #getting rewards for all epoch, a bit of a  bruteforce way querying for each epoch
    first_epoch = df2["stakeActivationEpoch"].astype(int).min()
    current_epoch = asyncio.run(getCurentEpoch())
    address_list = list(df["pubkey"].values)
    all_data_reward = getAllInflationRewards(address_list,range(first_epoch,current_epoch))
    df2["totalRewards"]=pd.DataFrame(all_data_reward).T["totalAmount"].astype(int)
    df2["currentDuration"]=df2["stakeDeactivationEpoch"].apply(lambda x:min(current_epoch,x))-df2["stakeActivationEpoch"]
    columns = ["stake","balance","stakeActivationEpoch","stakeDeactivationEpoch","totalRewards","currentDuration"]
    file = "snapchot_solana_delegator_epoch"+str(current_epoch)+"_"+str(datetime.datetime.now())[0:-16]
    print("saving snapchot to ",file)
    df2[columns].to_markdown(file)