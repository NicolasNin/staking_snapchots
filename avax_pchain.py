import requests
import json
import pandas as pd

#need access to api from a node or locally on a node
url = "http://127.0.0.1:9650/ext/P"
#url = "https://api.avax.network:9650/ext/P"

headers = {'Content-Type': 'application/json'}
def getDelegators():
    data = {
        "jsonrpc": "2.0",
        "method": "platform.getCurrentValidators",
        "params": {"nodeIDs":["NodeID-4QNnLZTYQPbZcFUoXmGoi2sWfdWFZ49aU",
        "NodeID-8PKikqQVFgRYLUwwNc2HHodNMyP6Tw6Qy"]},
        "id": 1
    }

    r = requests.post(url, data=json.dumps(data), headers=headers)
    data=r.json()["result"]
    validators = data["validators"]
    all_delegators=[]
    #'txID', 'startTime', 'endTime', 'stakeAmount', 'nodeID', 'rewardOwner', 'potentialReward', 'delegationFee', 'uptime', 'connected', 'delegators']
    data_validator={}
    for v in validators:
        data_validator[v["nodeID"]]={"delegationFee":float(v["delegationFee"]),
        "starTime":int(v["startTime"]),
        "endTime":int(v["endTime"]),
        "stakeAmount":int(v["stakeAmount"]),
        "rewardOwner":v["rewardOwner"]}
        all_delegators.extend(v["delegators"])
    for d in all_delegators:
        d["owners"] = d["rewardOwner"]["addresses"]
        d["owner"] = d["rewardOwner"]["addresses"][0]
        d["threshold"] = d["rewardOwner"]["threshold"]
        d["locktime"]=int(d["rewardOwner"]["locktime"])
        d["startTime"]=int(d["startTime"])
        d["endTime"]=int(d["endTime"])
        d["stakeAmount"]=int(d["stakeAmount"])
        d["potentialReward"]=int(d["potentialReward"])
        d["delegationFee"]=data_validator[d["nodeID"]]["delegationFee"]

    return all_delegators,data_validator


if __name__ =="__main__":
    delegators,validators = getDelegators()
    df = pd.DataFrame(delegators)
    columns = ["startTime", "endTime", "stakeAmount", "nodeID", "owner", "potentialReward","delegationFee"]
    df["netReward"] = df["potentialReward"]*(100-df["delegationFee"])/(100000000000)
    columns = ["startTime", "endTime", "stakeAmount", "nodeID", "owner", "potentialReward","delegationFee","netReward"]
    import datetime
    file = "snapchot_avalanche_delegator_"+str(datetime.datetime.now())[0:-10]
    print("saving snapchot to ",file)
    df[columns].to_markdown(file)
#     curl -X POST --data '{
#     "jsonrpc": "2.0",
#     "method": "platform.getTx",
#     "params": {
#         "txID":"tG7N6K1uLnTJmcCeXmPYrs6typ9nZLPd2PNyEa6tuJAbE8Kad",
#         "encoding": "cb58"
#     },
#     "id": 1
# }' -H 'content-type:application/json;' 127.0.0.1:9650/ext/P

