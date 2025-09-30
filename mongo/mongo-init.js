// // Initialize the replica set
// rs.initiate({
//     _id: 'rs0',
//     members: [
//         { _id: 0, host: 'mongo:27017' }
//     ]
// });

// // Use admin then create user root
// var adminDB = db.getSiblingDB('admin');
// adminDB.createUser({
//     user: 'superuser',
//     pwd: 'superuser',
//     roles: [{ role: 'root', db: 'admin' }]
// });

// // Authenticate as the root user
// adminDB.auth('superuser', 'superuser');

// // Create a new user in the target database
// var dbName = 'chat_gpt_db';
// var chatGptDb = db.getSiblingDB(dbName);
// chatGptDb.createUser({
//     user: 'sample',
//     pwd: 'sample',
//     roles: [{ role: 'readWrite', db: dbName }]
// });

rs.initiate();