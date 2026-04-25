import socket
import json
import chess
import threading
import sys
import time

# Client configuration
HOST = '127.0.0.1'
PORT = 5555
board = chess.Board()
color = None
game_id = None
last_move_time = time.time()
time_white = 900
time_black = 900

def receive_messages(conn):
    """Handle incoming server messages."""
    global board, color, game_id, last_move_time, time_white, time_black
    buffer = ""
    while True:
        try:
            data = conn.recv(1024).decode()
            if not data:
                print("Disconnected from server: No data received")
                break
            buffer += data

            while True:
                message, sep, rest = buffer.partition("\n")
                if not sep:
                    break
                buffer = rest
                message = message.strip()
                if not message:
                    continue
                try:
                    message = json.loads(message)
                except json.JSONDecodeError as e:
                    print(f"JSON decode error: {e} (message: {message})")
                    continue

                msg_type = message.get('type')

                if msg_type == 'lobby':
                    print(message.get('message'))

                elif msg_type == 'game_start':
                    color = message.get('color')
                    game_id = message.get('game_id')
                    print(f"Game started! You are {color}")
                    board.reset()
                    display_board()

                elif msg_type == 'game_state':
                    board = chess.Board(message['data']['board'])
                    time_white = message['data']['time_white']
                    time_black = message['data']['time_black']
                    last_move_time = time.time()
                    display_board()

                elif msg_type == 'chat':
                    print(message.get('message'))

                elif msg_type == 'error':
                    print(f"Error: {message.get('message')}")

                elif msg_type == 'game_over':
                    reason = message.get('reason', '')
                    result = message.get('result', '')
                    winner = message.get('winner', '')
                    message_text = message.get('message', '')

                    # Construct the game over message
                    game_over_msg = f"Game over: {result}"
                    if reason:
                        game_over_msg += f" ({reason})"
                    if message_text:
                        game_over_msg += f" - {message_text}"
                    if winner:
                        game_over_msg += f"\n{winner.capitalize()} has won the game!"
                    print(game_over_msg)
                    break

        except ConnectionError as e:
            print(f"Disconnected from server due to connection error: {e}")
            break
        except Exception as e:
            print(f"Unexpected error in receive_messages: {e}")
            time.sleep(1)

def display_board():
    """Display the chessboard in CLI."""
    print(board)
    if color:
        turn = 'White' if board.turn == chess.WHITE else 'Black'
        print(f"Turn: {turn}")
        print(f"Time remaining - White: {time_white:.1f} seconds")
        print(f"Time remaining - Black: {time_black:.1f} seconds")

def main():
    """Main client function."""
    conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        print(f"Attempting to connect to server at {HOST}:{PORT}...")
        conn.connect((HOST, PORT))
        print("Connected to server successfully!")
    except Exception as e:
        print(f"Failed to connect to server: {e}")
        return

    # Ask user if they want to be a player or spectator
    client_type = input("Enter 'player' or 'spectator': ").strip().lower()
    try:
        conn.send(json.dumps({'type': client_type}).encode() + b"\n")
    except Exception as e:
        print(f"Failed to send client type to server: {e}")
        conn.close()
        return

    # Start receiving messages
    receive_thread = threading.Thread(target=receive_messages, args=(conn,))
    receive_thread.daemon = True
    receive_thread.start()

    # Main loop for sending moves or chat
    while True:
        if client_type == 'spectator':
            msg = input("Chat: ").strip()
            if msg.lower() == 'quit':
                break
            try:
                conn.send(json.dumps({'type': 'chat', 'message': msg}).encode() + b"\n")
            except Exception as e:
                print(f"Failed to send chat message: {e}")
                break
        else:
            cmd = input("Enter move (e.g., e2e4), chat (prefix with 'chat:'), or 'resign' to end the game: ").strip()
            if cmd.lower() == 'quit':
                break
            if cmd.lower() == 'resign':
                try:
                    conn.send(json.dumps({'type': 'resign'}).encode() + b"\n")
                except Exception as e:
                    print(f"Failed to send resign command: {e}")
                    break
                break
            if cmd.startswith('chat:'):
                try:
                    conn.send(json.dumps({'type': 'chat', 'message': cmd[5:].strip()}).encode() + b"\n")
                except Exception as e:
                    print(f"Failed to send chat message: {e}")
                    break
            else:
                try:
                    conn.send(json.dumps({'type': 'move', 'move': cmd}).encode() + b"\n")
                except Exception as e:
                    print(f"Failed to send move: {e}")
                    break

    try:
        conn.close()
    except:
        pass
    print("Client disconnected.")

if __name__ == "__main__":
    main()