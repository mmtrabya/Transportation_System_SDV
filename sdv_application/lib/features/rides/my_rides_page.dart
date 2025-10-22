import 'package:flutter/material.dart';

class MyRidesPage extends StatelessWidget {
  const MyRidesPage({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final rides = [
      {'date': 'Today, 2:30 PM', 'from': 'City Center Mall', 'to': 'Tech Park Avenue', 'fare': '\$15.50', 'status': 'Completed'},
      {'date': 'Yesterday, 9:15 AM', 'from': 'Home - Oak Street', 'to': 'Downtown Office', 'fare': '\$12.30', 'status': 'Completed'},
      {'date': 'Oct 12, 6:45 PM', 'from': 'Shopping District', 'to': 'Riverside Park', 'fare': '\$18.90', 'status': 'Completed'},
    ];

    return Scaffold(
      appBar: AppBar(
        title: const Text('My Rides', style: TextStyle(fontWeight: FontWeight.bold)),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        colors: [
                          Theme.of(context).colorScheme.primary.withValues(alpha: 0.2),
                          Theme.of(context).colorScheme.secondary.withValues(alpha: 0.1),
                        ],
                      ),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Icon(Icons.receipt_long, size: 32, color: Theme.of(context).colorScheme.primary),
                  ),
                  const SizedBox(width: 16),
                  const Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Total Rides', style: TextStyle(fontSize: 14, color: Colors.grey)),
                        SizedBox(height: 4),
                        Text('3', style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold)),
                      ],
                    ),
                  ),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      const Text('Total Spent', style: TextStyle(fontSize: 14, color: Colors.grey)),
                      const SizedBox(height: 4),
                      Text('\$46.70', style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: Theme.of(context).colorScheme.primary)),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 24),
          const Text('Recent Trips', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
          const SizedBox(height: 16),
          ...rides.map((ride) => _buildRideCard(context, ride)),
        ],
      ),
    );
  }

  Widget _buildRideCard(BuildContext context, Map<String, String> ride) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(ride['date']!, style: const TextStyle(fontSize: 14, color: Colors.grey, fontWeight: FontWeight.w500)),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      colors: [Colors.green.withValues(alpha: 0.2), Colors.green.withValues(alpha: 0.1)],
                    ),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(ride['status']!, style: const TextStyle(color: Colors.green, fontSize: 12, fontWeight: FontWeight.bold)),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Column(
                  children: [
                    Container(
                      width: 12,
                      height: 12,
                      decoration: BoxDecoration(color: Theme.of(context).colorScheme.primary, shape: BoxShape.circle),
                    ),
                    Container(width: 2, height: 30, color: Colors.grey[300]),
                    Container(width: 12, height: 12, decoration: const BoxDecoration(color: Colors.green, shape: BoxShape.circle)),
                  ],
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(ride['from']!, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600)),
                      const SizedBox(height: 28),
                      Text(ride['to']!, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600)),
                    ],
                  ),
                ),
                Text(ride['fare']!, style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Theme.of(context).colorScheme.primary)),
              ],
            ),
          ],
        ),
      ),
    );
  }
}