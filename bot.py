import discord
from discord import app_commands

import json

intents = discord.Intents.all()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

from apscheduler.schedulers.asyncio import AsyncIOScheduler
import datetime

from db import users_session, User, server_session, Server

def log(m:str):
    if not log_in_txt_file:
        return
    with open("log.txt", "a") as file:
        file.write(f"{str(datetime.datetime.now())} - {str(m)}\n")

async def check_all_users():
    try:
        log("checking all users.")
        all_users = users_session.query(User).filter(User.check_at <= datetime.datetime.now()).all()
        for user in all_users:
            log(f"Checking {user.id}")
            server = server_session.query(Server).filter_by(id=user.guild).one_or_none()
            if server is None:
                log(f"Server with suspected id {user.guild} is none")
                continue
            if server.role_id is None:
                return
            discord_server = client.get_guild(server.id)
            discord_user = discord_server.get_member(user.id)
            if discord_user is None:
                log(f"User {user.id} already left")
                users_session.delete(user)
                users_session.commit()
                continue #discord user already left
            if not any(role.id == int(server.role_id) for role in discord_user.roles):
                await discord_user.send(f"You were automatically kicked from **{discord_server.name}** because you didn't verify in time.")
                await discord_user.kick(reason="Did not verify in time")
                users_session.delete(user)
                users_session.commit()
                log(f"User {str(user.id)} was kicked from {str(server.id)}")
            else:
                log(f"User {str(user.id)} is verified in {str(server.id)}")
                #user has role
                users_session.delete(user)
                users_session.commit()
    except Exception as e:
        print(f"Error at check_all_users: {str(e)}")

@client.event
async def on_ready():
    scheduler.start()
    print(f"Logged in as {client.user.name}")
    await tree.sync() #for /commands
    await client.change_presence(status=discord.Status.online, activity=discord.Game("!v help"))
    sync_guilds_with_db()

@client.event
async def on_member_join(member:discord.Member):
    print(f'{member} has joined the server {member.guild.id}')
    server = server_session.query(Server).filter_by(id=member.guild.id).one_or_none()
    if not server:
        return
    new_user = User(id=member.id, guild=member.guild.id, check_at=datetime.datetime.now() + datetime.timedelta(seconds=server.check_in_seconds))
    users_session.add(new_user)
    users_session.commit()

@client.event
async def on_guild_join(guild:discord.Guild):
    print(f'joined the server: "{guild.name}" (ID: {guild.id})')
    server = Server(id=guild.id)
    server_session.add(server)
    server_session.commit()

@client.event
async def on_guild_remove(guild:discord.Guild):
    print(f'removed from: "{guild.name}" (ID: {guild.id})')
    server = server_session.query(Server).filter_by(id=guild.id).one_or_none()
    if server:
        server_session.delete(server)
        server_session.commit()

@client.event
async def on_message(m:discord.Message):
    if m.author.bot:
        return
    if not m.content.startswith("!v"):
        return
    if not m.author.guild_permissions.administrator:
        return
    cmd = m.content.split("!v")[1].strip()
    if cmd == "help":
        embed = discord.Embed (
            title="Commands",
            description="!v help - View list of bot's commands\n!v time [TIME IN SECONDS] - Set the amount of time someone has until they are checked for the role\n!v role [ROLE @] - Set the role the bot tests for"
        )
        await m.reply(embed=embed)
    elif cmd.startswith("time"):
        new_time = cmd.split("time")[1].strip()
        try:
            new_time = int(new_time)
        except ValueError:
            await m.reply("Must be a number!")       
        server = server_session.query(Server).filter_by(id=m.guild.id).one_or_none()
        if not server:
            await m.reply("An error occured: Server not listed in our database!")      
            return
        server.check_in_seconds = new_time
        server_session.commit()
        await m.reply(f"Set role check time to {str(new_time)} seconds")
    elif cmd.startswith("role"):
        new_role = cmd.split("role")[1].strip().removeprefix("<@&").removesuffix(">").strip()
        if m.guild.get_role(int(new_role)) is None:
            await m.reply("Invalid role.")
            return
        server = server_session.query(Server).filter_by(id=m.guild.id).one_or_none()
        if not server:
            await m.reply("An error occured: Server not listed in our database!")      
            return
        server.role_id = new_role
        server_session.commit()
        await m.reply(f"Role to check for set to <@&{new_role}>")

token = ""
log_in_txt_file = False
with open("config.json", "r") as file:
    data = json.load(file)
    token = data["discord_bot_token"]
    log_in_txt_file = data["log_in_txt_file"]

def sync_guilds_with_db():
    #sync guilds with db while we were offline
    current_guilds = [guild.id for guild in client.guilds]
    for guild in server_session.query(Server).all():
        if guild.id in current_guilds:
            current_guilds.remove(guild.id)
        else:
            #the bot is gone from a server
            print(f'removed from: {guild.id}')
            log(f'removed from: {guild.id}')
            server_session.delete(guild)
    #the remaining guilds are those not removed and not in the db
    for guild in current_guilds:
        #added to a server
        print(f'added to: {str(guild)}')
        log(f'added to: {str(guild)}')
        new_guild = Server(id=guild)
        server_session.add(new_guild)
    server_session.commit()

scheduler = AsyncIOScheduler()
scheduler.add_job(check_all_users, 'interval', seconds=5)  #Check every 5 seconds
#scheduler.start()
client.run(token=token)

#shut down the scheduler when exiting
import atexit
atexit.register(lambda: scheduler.shutdown())